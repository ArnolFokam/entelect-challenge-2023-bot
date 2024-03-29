import numpy as np
from collections import deque

import gym
from gym import spaces

from ecbot.connection import Constants
from ecbot.envs.cyfi import CyFi
from ecbot.envs.rewards import reward_fn

class SinglePlayerSingleAgentEnv(CyFi):
    
    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)
        
        # Our CiFy agent has 12 possible actions
        # UP - 1
        # DOWN- 2
        # LEFT - 3
        # RIGHT - 4
        # UPLEFT - 5
        # UPRIGHT - 6
        # DOWNLEFT - 7
        # DOWNRIGHT - 8
        # DIGDOWN - 9
        # DIGLEFT - 10
        # DIGRIGHT - 11
        # STEAL - 12 (WIP wrench)
        self.action_space = gym.spaces.Discrete(12)
        
        # Our CiFy agent only knows about its windowed view of the world
        # Note: the agent is at the center of the window
        self.observation_space = spaces.Box(low=0.0, high=1.0, shape=(34 * 22,), dtype=float)
        
        self.reward_fn = reward_fn[self.cfg.reward_fn](self.cfg)
        self.past_k_rewards = deque([], maxlen=self.cfg.reward_backup_len) 


    def step(self, action: int):
        
        # command from the  game server are 1-indexed
        self.game_client.send_player_command(int(action + 1))
        self._wait_for_game_state()
        
        self.observation, self.info, done = self._return_env_state()
        reward, _ = self.reward_fn(self.info)
        
        self.past_k_rewards.append(reward)
        print(f"reward: {reward}, mean: {np.mean(self.past_k_rewards)}")
        truncated =  np.mean(self.past_k_rewards) < self.cfg.past_reward_threshold
        return self.observation, reward, done, truncated, self.info
    
    def reset(self):
        observation = super().reset()
        self.past_k_rewards = deque([], maxlen=self.cfg.reward_backup_len)
        self.reward_fn.reset(self.info)
        return observation
        
    def _get_observation(self, game_state):
        return np.array(game_state[Constants.HERO_WINDOW], dtype=np.uint8).flatten() / 6.0
        
    def _get_info(self, game_state):
        info =  {
            "position": (
                game_state[Constants.POSITION_X],
                game_state[Constants.POSITION_Y],
            ),
            "window": np.rot90(game_state[Constants.HERO_WINDOW]),
            "elapsed_time": game_state[Constants.ELAPSED_TIME],
            "collected": game_state[Constants.COLLECTED],
            "current_level": game_state[Constants.CURRENT_LEVEL],
            "hazards_hits": 0,
        }
        
        # custom info (add for reward function)
        if Constants.HazardsHits in game_state:
            info["hazards_hits"] = game_state[Constants.HazardsHits]
                       
        return info

class SinglePlayerSingleAgentEnvV2(SinglePlayerSingleAgentEnv):
    
    def step(self, action: int):
        
        # command from the  game server are 1-indexed
        self.game_client.send_player_command(int(action + 1))
        self._wait_for_game_state()
        
        self.observation, self.info, done = self._return_env_state()
        
        reward, reward_events = self.reward_fn(self.info, )
        was_on_bad_floor = reward_events["on_bad_floor"]
        
        self.past_k_rewards.append(reward)
        print(f"reward: {reward}, mean: {np.mean(self.past_k_rewards)}")
        truncated = was_on_bad_floor or np.mean(self.past_k_rewards) < self.cfg.past_reward_threshold
        return self.observation, reward, done, truncated, self.info