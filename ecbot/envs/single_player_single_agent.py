import numpy as np
from collections import defaultdict, deque

import gym
from gym import spaces

from ecbot.connection import Constants
from ecbot.envs.cyfi import CyFi

class SinglePlayerSingleAgentEnv(CyFi):
    
    def __init__(self, cfg):

        super().__init__(cfg)
        
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
        self.observation_space = spaces.Box(low=0, high=6, shape=(34 * 22,), dtype=int)
        
        # to calculate reward
        self.decay_factor = 0.3
        self.reward_backup_len = 15
        self.past_reward_threshold = 0.01
        self.position_reward = defaultdict(lambda : 10)
        self.past_k_rewards = deque([], maxlen=self.reward_backup_len) 
        
    def _calculate_reward(self, position, *args, **kwargs):
        reward = self.position_reward[position]
        
        # decay the reward
        self.position_reward[position] = reward * self.decay_factor
        
        return reward
        
    def step(self, action: int):
        
        # command from the  game server are 1-indexed
        self.game_client.send_player_command(int(action + 1))
        self._wait_for_game_state()
        
        self.observation, self.info, done = self._return_env_state()
        reward = self._calculate_reward(self.info["position"])
        
        self.past_k_rewards.append(reward)
        done = done or np.mean(self.past_k_rewards) < self.past_reward_threshold
        return self.observation, reward, done, self.info
    
    def reset(self):
        observation = super().reset()
        self.past_k_rewards = deque([], maxlen=self.reward_backup_len) 
        self.position_reward = defaultdict(lambda : 10)
        return observation
        
    def _get_observation(self, game_state):
        return np.array(game_state[Constants.HERO_WINDOW], dtype=np.uint8).flatten()
        
    def _get_info(self, game_state):
        return {
            "position": (
                game_state[Constants.POSITION_X],
                game_state[Constants.POSITION_Y],
            ),
            "window": np.rot90(game_state[Constants.HERO_WINDOW]),
            "elapsed_time": game_state[Constants.ELAPSED_TIME],
            "collected": game_state[Constants.COLLECTED],
            "current_level": game_state[Constants.CURRENT_LEVEL]
        }
