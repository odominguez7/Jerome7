"""AgentMesh — The global mesh network coordinator.

Ties together the registry, protocol, message bus, and collective
insights into a single entry point for the rest of the codebase.
"""

from datetime import datetime, timedelta, date

from sqlalchemy import func
from sqlalchemy.orm import Session as DBSession

from src.db.models import User, Streak, Event

from src.agents.mesh.agent_registry import AgentRegistry
from src.agents.mesh.a2a_protocol import A2AProtocol
from src.agents.mesh.message_bus import MessageBus
from src.agents.mesh.collective_insights import CollectiveInsights


class AgentMesh:
    """Manages the global agent mesh network."""

    def __init__(self, db_session: DBSession):
        self.db = db_session
        self.registry = AgentRegistry(db_session)
        self.protocol = A2AProtocol(db_session)
        self.bus = MessageBus()
        self.insights = CollectiveInsights()

    async def register_agent(self, user_id: str) -> dict:
        """Register a personal agent for a user. Returns agent card.

        Pulls user data from the DB to build the card, computes an
        initial wellness score, and subscribes the agent to the bus.
        """
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError(f"User {user_id} not found")

        streak = self.db.query(Streak).filter(Streak.user_id == user_id).first()
        wellness = await self.registry.compute_wellness_score(user_id)

        card = {
            "agent_id": user_id,
            "user_id": user_id,
            "name": user.name,
            "timezone": user.timezone,
            "goal": user.goal.value if user.goal else "just_try",
            "fitness_level": user.fitness_level.value if user.fitness_level else "beginner",
            "status": "active",
            "wellness_score": wellness,
            "current_streak": streak.current_streak if streak else 0,
            "registered_at": datetime.utcnow().isoformat(),
            "last_heartbeat": datetime.utcnow().isoformat(),
        }

        agent_id = await self.registry.register(user_id, card)

        # Subscribe to the in-memory bus with a no-op handler.
        # Real handlers can be attached later via bus.subscribe().
        self.bus.subscribe(agent_id, lambda msg: None)

        # Announce registration to other agents
        self.bus.publish({
            "message_type": "agent_registered",
            "from_agent": agent_id,
            "payload": {
                "name": user.name,
                "timezone": user.timezone,
                "goal": card["goal"],
            },
        })

        return card

    async def broadcast_insight(self, insight_type: str, data: dict) -> None:
        """Broadcast a collective insight to all agents.

        Sends via both the persistent A2A protocol (for offline agents)
        and the in-memory bus (for live agents).
        """
        # Persistent broadcast
        count = await self.protocol.broadcast(
            from_agent="mesh:system",
            message_type=f"insight:{insight_type}",
            payload=data,
        )

        # In-memory broadcast
        self.bus.publish({
            "message_type": f"insight:{insight_type}",
            "from_agent": "mesh:system",
            "payload": data,
        })

        print(f"[AgentMesh] Broadcast insight:{insight_type} to {count} agents")

    async def find_accountability_pair(self, user_id: str) -> dict:
        """Find the best accountability partner for a user.

        Matching criteria (weighted):
        1. Same timezone or +/- 2 hours (40%)
        2. Same goal (30%)
        3. Similar streak length +/- 5 days (20%)
        4. Similar fitness level (10%)

        Returns the best match with a compatibility score.
        """
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError(f"User {user_id} not found")

        streak = self.db.query(Streak).filter(Streak.user_id == user_id).first()
        user_streak = streak.current_streak if streak else 0
        user_goal = user.goal.value if user.goal else "just_try"
        user_fitness = user.fitness_level.value if user.fitness_level else "beginner"

        # Get all other active agents
        agents = await self.registry.discover({"status": "active"})
        candidates = [a for a in agents if a.get("agent_id") != user_id]

        if not candidates:
            return {
                "matched": False,
                "reason": "No other active agents in the mesh",
            }

        scored = []
        for candidate in candidates:
            score = 0.0

            # Timezone proximity (40 points max)
            tz_score = self._timezone_compatibility(
                user.timezone, candidate.get("timezone", "UTC")
            )
            score += tz_score * 40.0

            # Goal match (30 points)
            if candidate.get("goal") == user_goal:
                score += 30.0
            elif candidate.get("goal") in ("move_more", "just_try") and user_goal in ("move_more", "just_try"):
                score += 15.0  # partial match for similar goals

            # Streak similarity (20 points)
            c_streak = candidate.get("current_streak", 0)
            streak_diff = abs(user_streak - c_streak)
            if streak_diff <= 2:
                score += 20.0
            elif streak_diff <= 5:
                score += 15.0
            elif streak_diff <= 10:
                score += 8.0

            # Fitness level (10 points)
            if candidate.get("fitness_level") == user_fitness:
                score += 10.0
            else:
                # Adjacent levels get partial credit
                levels = ["beginner", "returning", "active"]
                try:
                    diff = abs(
                        levels.index(user_fitness)
                        - levels.index(candidate.get("fitness_level", "beginner"))
                    )
                    if diff == 1:
                        score += 5.0
                except ValueError:
                    pass

            scored.append((candidate, score))

        scored.sort(key=lambda x: x[1], reverse=True)
        best_match, best_score = scored[0]

        return {
            "matched": True,
            "partner": {
                "agent_id": best_match.get("agent_id"),
                "name": best_match.get("name"),
                "timezone": best_match.get("timezone"),
                "goal": best_match.get("goal"),
                "streak": best_match.get("current_streak", 0),
            },
            "compatibility_score": round(best_score, 1),
            "max_score": 100.0,
        }

    async def run_daily_checkups(self) -> list:
        """Run daily health checkups across all registered agents.

        For each agent:
        1. Recompute wellness score
        2. Detect status changes (active -> at_risk -> idle)
        3. Refresh streak data in the card
        4. Generate interventions if needed

        Returns a list of status change events.
        """
        agents = await self.registry.discover()
        changes = []
        today = date.today()

        for agent_card in agents:
            agent_id = agent_card.get("agent_id")
            if not agent_id:
                continue

            user = self.db.query(User).filter(User.id == agent_id).first()
            if not user:
                continue

            streak = self.db.query(Streak).filter(Streak.user_id == agent_id).first()

            # Recompute wellness
            new_wellness = await self.registry.compute_wellness_score(agent_id)
            old_wellness = agent_card.get("wellness_score", 50.0)
            old_status = agent_card.get("status", "active")

            # Determine new status
            new_status = old_status
            days_since_session = None
            if streak and streak.last_session_date:
                days_since_session = (today - streak.last_session_date).days

                if days_since_session == 0:
                    new_status = "active"
                elif days_since_session <= 2:
                    new_status = "active"
                elif days_since_session <= 5:
                    new_status = "at_risk"
                elif days_since_session <= 14:
                    new_status = "idle"
                else:
                    new_status = "offline"
            elif streak is None:
                # New user, no sessions yet
                new_status = "active" if agent_card.get("status") == "active" else "idle"

            # Update the registry
            current_streak = streak.current_streak if streak else 0
            await self.registry.update_status(agent_id, new_status, new_wellness)

            # Update streak in card
            event = (
                self.db.query(Event)
                .filter(
                    Event.event_type == "mesh:agent_card",
                    Event.user_id == agent_id,
                )
                .first()
            )
            if event and event.payload:
                card = dict(event.payload)
                card["current_streak"] = current_streak
                card["name"] = user.name
                card["timezone"] = user.timezone
                card["goal"] = user.goal.value if user.goal else "just_try"
                event.payload = card
                self.db.commit()

            # Record status change
            if new_status != old_status or abs(new_wellness - old_wellness) > 10:
                change = {
                    "agent_id": agent_id,
                    "name": user.name,
                    "old_status": old_status,
                    "new_status": new_status,
                    "old_wellness": old_wellness,
                    "new_wellness": new_wellness,
                    "current_streak": current_streak,
                    "days_since_session": days_since_session,
                }
                changes.append(change)

                # Notify via bus
                self.bus.publish({
                    "message_type": "status_change",
                    "from_agent": "mesh:system",
                    "payload": change,
                })

        return changes

    async def get_mesh_status(self) -> dict:
        """Return current mesh status: active agents, messages sent, insights generated."""
        active_count = await self.registry.get_active_count()
        all_agents = await self.registry.discover()
        total_agents = len(all_agents)

        # Count A2A messages in the last 24h
        yesterday = datetime.utcnow() - timedelta(hours=24)
        a2a_count = (
            self.db.query(func.count(Event.id))
            .filter(
                Event.event_type.like("a2a:%"),
                Event.created_at >= yesterday,
            )
            .scalar()
        ) or 0

        # Count insights generated
        insight_count = (
            self.db.query(func.count(Event.id))
            .filter(
                Event.event_type == "mesh:collective_insight",
                Event.created_at >= yesterday,
            )
            .scalar()
        ) or 0

        # Status distribution
        status_dist = {}
        for agent in all_agents:
            status = agent.get("status", "unknown")
            status_dist[status] = status_dist.get(status, 0) + 1

        # Wellness distribution
        wellness_scores = [
            a.get("wellness_score", 0) for a in all_agents
            if a.get("wellness_score") is not None
        ]
        avg_wellness = (
            sum(wellness_scores) / len(wellness_scores) if wellness_scores else 0
        )

        return {
            "total_agents": total_agents,
            "active_agents": active_count,
            "status_distribution": status_dist,
            "messages_24h": a2a_count,
            "insights_24h": insight_count,
            "bus_subscribers": self.bus.subscriber_count,
            "bus_messages_total": self.bus.total_messages,
            "avg_wellness_score": round(avg_wellness, 1),
            "timestamp": datetime.utcnow().isoformat(),
        }

    # ---- Private helpers ----

    def _timezone_compatibility(self, tz_a: str, tz_b: str) -> float:
        """Compute timezone compatibility score (0.0-1.0).

        Uses a simple heuristic: extract UTC offset from timezone name
        or assume 0 if unknown. Closer offsets score higher.
        """
        offset_a = self._estimate_utc_offset(tz_a)
        offset_b = self._estimate_utc_offset(tz_b)
        diff = abs(offset_a - offset_b)

        if diff == 0:
            return 1.0
        elif diff <= 1:
            return 0.85
        elif diff <= 2:
            return 0.7
        elif diff <= 3:
            return 0.5
        elif diff <= 6:
            return 0.25
        else:
            return 0.1

    def _estimate_utc_offset(self, timezone: str) -> int:
        """Estimate UTC offset from IANA timezone string.

        This is a rough heuristic — good enough for matching.
        For precise offsets, use pytz or zoneinfo.
        """
        tz_offsets = {
            "US/Eastern": -5, "America/New_York": -5, "EST": -5,
            "US/Central": -6, "America/Chicago": -6, "CST": -6,
            "US/Mountain": -7, "America/Denver": -7, "MST": -7,
            "US/Pacific": -8, "America/Los_Angeles": -8, "PST": -8,
            "Europe/London": 0, "GMT": 0, "UTC": 0,
            "Europe/Paris": 1, "Europe/Berlin": 1, "CET": 1,
            "Europe/Helsinki": 2, "EET": 2,
            "Europe/Moscow": 3,
            "Asia/Dubai": 4,
            "Asia/Kolkata": 5, "Asia/Calcutta": 5,
            "Asia/Bangkok": 7,
            "Asia/Shanghai": 8, "Asia/Hong_Kong": 8, "Asia/Singapore": 8,
            "Asia/Tokyo": 9,
            "Australia/Sydney": 11,
            "Pacific/Auckland": 12,
        }

        if timezone in tz_offsets:
            return tz_offsets[timezone]

        # Try to match partial names
        tz_lower = timezone.lower()
        for known, offset in tz_offsets.items():
            if known.lower() in tz_lower or tz_lower in known.lower():
                return offset

        return 0  # default to UTC
