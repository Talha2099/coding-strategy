from typing import Any, Tuple, Dict
import numpy as np

class ExecutionEnv:
    """
    Gym-style environment for execution optimization.
    Goal: Decide between Market/Limit, delayed entry, and exit logic.
    """
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.state = None
        self.observation_space = None # Box(low=-np.inf, high=np.inf, shape=(10,))
        self.action_space = None # Discrete(5)

    def reset(self) -> np.ndarray:
        # [pnl, ofi, imbalance, spread, volatility, trade_intensity, hour, side, in_position, session_type]
        self.state = np.zeros(10)
        return self.state

    def step(self, action: int) -> Tuple[np.ndarray, float, bool, Dict]:
        """
        Actions: 0: Hold, 1: Enter Market, 2: Post Limit, 3: Partial Exit, 4: Close
        """
        reward = 0.0
        done = False
        
        # Simple simulation of reward: 
        # Favorable OFI when entering market increases reward
        ofi = self.state[1]
        
        if action == 1: # Enter Market
            reward = ofi * 0.1 # Directional alignment reward
            self.state[8] = 1.0 # In position
            
        elif action == 4: # Close
            pnl = self.state[0]
            reward = pnl
            done = True
            
        # Time decay penalty to encourage faster execution optimality
        reward -= 0.001
        
        return self.state, reward, done, {}
