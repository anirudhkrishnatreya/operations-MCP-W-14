import crewai.llms.cache as _crewai_cache
from crewai.experimental.agent_executor import AgentExecutor


def apply_patches():
    """Apply all necessary monkey-patches for CrewAI to function properly."""
    _patch_agent_executor_human_input()
    _patch_crewai_cache()


def _patch_agent_executor_human_input():
    """Monkey-patch AgentExecutor to bridge ask_for_human_input to its state (CrewAI 1.14.6 bug fix)."""
    if not hasattr(AgentExecutor, "ask_for_human_input"):
        AgentExecutor.ask_for_human_input = property(
            lambda self: (
                self.state.ask_for_human_input if hasattr(self, "state") else False
            ),
            lambda self, v: (
                setattr(self.state, "ask_for_human_input", v)
                if hasattr(self, "state")
                else None
            ),
        )

    if not hasattr(AgentExecutor, "messages"):
        AgentExecutor.messages = property(
            lambda self: self.state.messages if hasattr(self, "state") else [],
            lambda self, v: (
                setattr(self.state, "messages", v) if hasattr(self, "state") else None
            ),
        )

    if not hasattr(AgentExecutor, "_format_feedback_message"):

        def _format_feedback_message(self, feedback: str):
            from crewai.utilities.agent_utils import format_message_for_llm
            from crewai.utilities.i18n import I18N_DEFAULT

            return format_message_for_llm(
                I18N_DEFAULT.slice("feedback_instructions").format(feedback=feedback)
            )

        AgentExecutor._format_feedback_message = _format_feedback_message


def _patch_crewai_cache():
    """Monkey-patch to prevent 'cache_breakpoint' from being added to messages (Groq unsupported property bug)."""
    _crewai_cache.mark_cache_breakpoint = lambda msg: msg
