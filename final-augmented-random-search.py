# importação das bibliotecas
import os
import numpy as np
import gym
from gym import wrappers
import pybullet_envs

# configuração dos hiperparametros
class Hp():
    def __init__(self):
        self.nb_steps = 1000 # numero de episódios
        self.episode_lenght = 1000 # máxima duração dos episódios
        self.learning_rate = 0.02 # taxa de aprendizado
        self.nb_directions = 16 # numero de direções, matrizes de perturbações contruidas
        self.nb_best_directions = 16 # mellhores recompensas
        assert self.nb_best_directions <= self.nb_directions # garantir que o best directions é menor que o directions
        self.noise = 0.03 # ruido, filtro de variancia nos dados
        self.seed = 1 # manter os resultados
        self.env_name = 'HalfCheetahBulletEnv-v0'

# normalização dos estados
class Normalizer():
    def __init__(self, nb_inputs):
        self.n = np.zeros(nb_inputs) # numero de entradas, inicializando com valores 0
        self.mean = np.zeros(nb_inputs) 
        self.mean_diff = np.zeros(nb_inputs)
        self.var = np.zeros(nb_inputs)
    
    def observe(self, x): # x será um vetor
        self.n += 1.
        last_mean = self.mean.copy()
        self.mean += (x - self.mean) / self.n
        self.mean_diff += (x - last_mean) * (x - self.mean)
        self.var = (self.mean / self.n).clip(min = 1e-2) # não pode ser menor que 0.001

    def normalize(self, inputs):
        obs_mean = self.mean
        obs_std = np.sqrt(self.var)
        return (inputs - obs_mean) / obs_std    

# contrução da Inteligência
class Policy():
    def __init__(self, input_size, output_size):
        self.theta = np.zeros((output_size, input_size)) # matriz de pesos
    
    def evaluate(self, input, delta = None, direction = None):
        if direction is None:
            return self.theta.dot(input)
        
        elif direction == 'positive':
            return (self.theta + hp.noise * delta).dot(input)

        else:
            return (self.theta - hp.noise * delta).dot(input)
    
    def sample_deltas(self):
        return [np.random.randn(*self.theta.shape) for _ in range(hp.nb_directions)]

    # atualização dos pesos
    # rollouts ( recompensa positiva, recompensa negativa, pertubação)
    # sigma_r ( desvio padrão das recompensas )
    def update(self, rollouts, sigma_r):
        step = np.zeros(self.theta.shape)
        for r_pos, r_neg, d in rollouts:
            step += (r_pos - r_neg) * d 
        self.theta += hp.learning_rate / (hp.nb_best_directions * sigma_r) * step

def explore(env, normalizer, policy, direction = None, delta = None):
    state = env.reset()
    done = False
    num_place = 0.
    sum_rewards = 0 # fazer um teste com a média
    while not done and num_place < hp.episode_lenght:
        normalizer.observe(state)
        state = normalizer.normalize(state)
        action = policy.evaluate(state, delta, direction)
        state, reward, done, _ = env.step(action)
        reward = max(min(reward, 1), -1) # filtro para recompensas entre -1 e 1
        sum_rewards += reward 
        num_place += 1 
    
    return sum_rewards

# treinamento da inteligência artificial
def train(env, policy, normalizer, hp):
    for step in range(hp.nb_steps):
        # inicialização das pertubações(deltas) e as recompensas positivas e negativas
        deltas = policy.sample_deltas()
        positive_rewards = [0] * hp.nb_directions
        negative_rewards = [0] * hp.nb_directions

        # recompensas das direções positivas
        for k in range(hp.nb_directions):
            positive_rewards[k] = explore(env, normalizer, policy, direction = 'positive', delta = deltas[k])

        # recompensas das direções negativas
        for k in range(hp.nb_directions):
            negative_rewards[k] = explore(env, normalizer, policy, direction = 'negative', delta = deltas[k])

        # todas as recompensas para calcular desvio padrão
        all_rewards = np.array(positive_rewards + negative_rewards)
        sigma_r = all_rewards.std()

        # ordenanção dos rollouts
        scores = {k: max(r_pos, r_neg) for k, (r_pos, r_neg) in enumerate(zip(positive_rewards, negative_rewards))}
        order = sorted(scores.keys(), key= lambda x: scores[x], reverse=True)[:hp.nb_best_directions]
        rollouts = [(positive_rewards[k], negative_rewards[k], deltas[k]) for k in order]
        
        # atualização da potilica(atualização dos pesos)
        policy.update(rollouts, sigma_r)

        # impressão da recompensa final
        reward_evaluation= explore(env, normalizer, policy)
        print('Step: ', step,'Reward: ', reward_evaluation)

# execução do codigo principal
def mkdir(base, name):
    path = os.path.join(base, name)
    if not os.path.exists(path):
        os.makedirs(path)
    return path
work_dir = mkdir('exp', 'brs')
monitor_dir = mkdir(work_dir, 'monitor')

hp = Hp()
np.random.seed(hp.seed)
env = gym.make(hp.env_name)
env = wrappers.Monitor(env, monitor_dir, force=True)
nb_inputs = env.observation_space.shape[0]
nb_outputs = env.action_space.shape[0]
policy = Policy(nb_inputs, nb_outputs)
normalizer = Normalizer(nb_inputs)

train(env, policy, normalizer, hp)