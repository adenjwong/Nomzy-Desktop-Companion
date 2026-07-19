from dataclasses import dataclass
from enum import Enum, auto


class CompanionState(Enum):
    IDLE = auto()
    WALKING = auto()
    BLINKING = auto()
    SITTING = auto()
    SLEEPING = auto()
    TALKING = auto()
    REACTING = auto()
    DRAGGING = auto()
    PAUSED = auto()
    MENU = auto()


class CompanionEvent(Enum):
    START_WALKING = auto()
    STOP_WALKING = auto()
    START_BLINKING = auto()
    START_SITTING = auto()
    START_SLEEPING = auto()
    START_TALKING = auto()
    STOP_TALKING = auto()
    START_REACTION = auto()
    START_DRAGGING = auto()
    STOP_DRAGGING = auto()
    PAUSE = auto()
    RESUME = auto()
    OPEN_MENU = auto()
    CLOSE_MENU = auto()
    ANIMATION_FINISHED = auto()


@dataclass(frozen=True)
class StateTransition:
    event: CompanionEvent
    previous: CompanionState
    current: CompanionState

    @property
    def changed(self) -> bool:
        return self.previous is not self.current


class CompanionStateMachine:
    """Owns Nomzy's activity and the rules for interrupting activities."""

    def __init__(self, animation_names: dict[CompanionState, str]):
        required_states = set(CompanionState) - {CompanionState.REACTING}
        missing_states = required_states - animation_names.keys()
        if missing_states:
            missing = ", ".join(
                sorted(state.name.lower() for state in missing_states)
            )
            raise ValueError(f"Missing activity animations: {missing}")

        self.animation_names = dict(animation_names)
        self.state = CompanionState.IDLE
        self.paused = False
        self.menu_open = False
        self.message_active = False
        self.reaction_animation: str | None = None
        self._animation_restart_pending = False

    @property
    def animation_name(self) -> str:
        if self.state is CompanionState.REACTING:
            return self.reaction_animation or "pet"
        return self.animation_names[self.state]

    @property
    def is_dragging(self) -> bool:
        return self.state is CompanionState.DRAGGING

    @property
    def blocks_background_updates(self) -> bool:
        return self.paused or self.menu_open

    def consume_animation_restart(self) -> bool:
        restart = self._animation_restart_pending
        self._animation_restart_pending = False
        return restart

    def dispatch(
        self,
        event: CompanionEvent,
        animation_name: str | None = None,
    ) -> StateTransition:
        previous = self.state
        target = previous
        restart = False

        if event is CompanionEvent.START_WALKING:
            if previous is CompanionState.IDLE:
                target = CompanionState.WALKING
        elif event is CompanionEvent.STOP_WALKING:
            if previous is CompanionState.WALKING:
                target = self._settled_state()
        elif event in {
            CompanionEvent.START_BLINKING,
            CompanionEvent.START_SITTING,
            CompanionEvent.START_SLEEPING,
        }:
            if previous is CompanionState.IDLE:
                target = {
                    CompanionEvent.START_BLINKING: CompanionState.BLINKING,
                    CompanionEvent.START_SITTING: CompanionState.SITTING,
                    CompanionEvent.START_SLEEPING: CompanionState.SLEEPING,
                }[event]
        elif event is CompanionEvent.START_TALKING:
            self.message_active = True
            if previous not in {
                CompanionState.REACTING,
                CompanionState.DRAGGING,
                CompanionState.PAUSED,
                CompanionState.MENU,
            }:
                target = CompanionState.TALKING
                restart = True
        elif event is CompanionEvent.STOP_TALKING:
            self.message_active = False
            if previous is CompanionState.TALKING:
                target = self._settled_state()
        elif event is CompanionEvent.START_REACTION:
            if previous is not CompanionState.DRAGGING:
                reaction_changed = self.reaction_animation != animation_name
                self.reaction_animation = animation_name or "pet"
                if previous not in {CompanionState.PAUSED, CompanionState.MENU}:
                    target = CompanionState.REACTING
                    restart = reaction_changed or previous is CompanionState.REACTING
        elif event is CompanionEvent.START_DRAGGING:
            self.menu_open = False
            self.reaction_animation = None
            target = CompanionState.DRAGGING
            restart = previous is CompanionState.DRAGGING
        elif event is CompanionEvent.STOP_DRAGGING:
            if previous is CompanionState.DRAGGING:
                target = self._settled_state()
        elif event is CompanionEvent.PAUSE:
            self.paused = True
            if previous is not CompanionState.DRAGGING:
                target = CompanionState.MENU if self.menu_open else CompanionState.PAUSED
        elif event is CompanionEvent.RESUME:
            self.paused = False
            if previous is CompanionState.PAUSED:
                target = self._settled_state()
        elif event is CompanionEvent.OPEN_MENU:
            self.menu_open = True
            self.message_active = False
            target = CompanionState.MENU
        elif event is CompanionEvent.CLOSE_MENU:
            self.menu_open = False
            if previous is CompanionState.MENU:
                target = self._settled_state()
        elif event is CompanionEvent.ANIMATION_FINISHED:
            if animation_name == self.animation_name:
                if previous is CompanionState.REACTING:
                    self.reaction_animation = None
                    target = self._settled_state()
                elif previous in {
                    CompanionState.BLINKING,
                    CompanionState.SITTING,
                    CompanionState.SLEEPING,
                }:
                    target = self._settled_state()

        if previous is CompanionState.REACTING and target is not CompanionState.REACTING:
            if event not in {
                CompanionEvent.PAUSE,
                CompanionEvent.OPEN_MENU,
            }:
                self.reaction_animation = None

        self.state = target
        if target is not previous or restart:
            self._animation_restart_pending = True

        return StateTransition(event, previous, target)

    def _settled_state(self) -> CompanionState:
        if self.menu_open:
            return CompanionState.MENU
        if self.paused:
            return CompanionState.PAUSED
        if self.reaction_animation:
            return CompanionState.REACTING
        if self.message_active:
            return CompanionState.TALKING
        return CompanionState.IDLE


class CompanionActivityMixin:
    def transition_activity(
        self,
        event: CompanionEvent,
        animation_name: str | None = None,
    ) -> StateTransition:
        transition = self.activity.dispatch(event, animation_name)
        interrupts_movement = event in {
            CompanionEvent.START_TALKING,
            CompanionEvent.START_REACTION,
            CompanionEvent.START_DRAGGING,
            CompanionEvent.OPEN_MENU,
            CompanionEvent.PAUSE,
        }
        stopped_walking = (
            transition.previous is CompanionState.WALKING
            and transition.current is not CompanionState.WALKING
        )

        if interrupts_movement or stopped_walking:
            self.walk_step_x = 0
            self.walk_step_y = 0
            self.scheduler.reset_walk()

        return transition
