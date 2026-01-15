import logging

from agents.base import AgentBase

logger = logging.getLogger(__name__)


class CausalMemoryAgent(AgentBase):
    name = "causal_memory"

    def update_memory(self, intents, outcomes) -> None:
        _ = (intents, outcomes)
        logger.info("CausalMemoryAgent.update_memory not implemented yet")
