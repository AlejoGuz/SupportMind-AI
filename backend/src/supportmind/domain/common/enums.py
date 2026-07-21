from enum import Enum


class TicketStatus(str, Enum):
    NEW = "new"
    OPEN = "open"
    PENDING = "pending"
    ON_HOLD = "on_hold"
    RESOLVED = "resolved"
    CLOSED = "closed"


class Priority(str, Enum):
    P1 = "P1"
    P2 = "P2"
    P3 = "P3"
    P4 = "P4"


class Sentiment(str, Enum):
    NEGATIVE = "negative"
    NEUTRAL = "neutral"
    POSITIVE = "positive"


class Channel(str, Enum):
    CELU_CHAT = "celu_chat"


class ConversationOutcome(str, Enum):
    RESOLVED = "resolved"
    ESCALATED = "escalated"
    ABANDONED = "abandoned"
    BLOCKED_BY_INCIDENT = "blocked_by_incident"


class NodeType(str, Enum):
    QUESTION = "question"
    RESOLVE = "resolve"
    ESCALATE = "escalate"


class AlertRequestStatus(str, Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    EXPIRED = "expired"


class IncidentStatus(str, Enum):
    ACTIVE = "active"
    MONITORING = "monitoring"
    RESOLVED = "resolved"


class AgentRole(str, Enum):
    ADMIN = "admin"
    SUPERVISOR = "supervisor"
    AGENT_L1 = "agent_l1"
    AGENT_L2 = "agent_l2"


class AgentAvailability(str, Enum):
    AVAILABLE = "available"
    BUSY = "busy"
    OFFLINE = "offline"


class AlertDecisionType(str, Enum):
    ACCEPT = "accept"
    REJECT = "reject"
