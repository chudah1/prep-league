"""Neural-network building blocks powered by the local autograd engine."""

from __future__ import annotations

import random
from collections.abc import Sequence

from engine import Value


class Neuron:
    def __init__(self, nin: int) -> None:
        # how many inputs to my neuron
        self.w = [Value(random.uniform(-1, 1)) for _ in range(nin)]
        self.b = Value(0.0)

    def __call__(self, x):
        activation = sum((w *x for (w,x) in zip(self.w,x)), self.b)
        return activation.tanh()

    def parameters(self):
        return self.w + [self.b]

class Layer:

    def __init__(self, nin, nout):
        # how many neurons in each layer
        self.neurons = [Neuron(nin) for _ in range(nout)]

    def __call__(self, x):
        output = [n(x) for n in self.neurons]
        return output[0] if len(output) == 1 else output

    def parameters(self):
        return [out for n in self.neurons for out in n.parameters()]

class MLP:
    def __init__(self, nin, nouts:list):
        mlp_size = [nin] + nouts
        self.layers = [Layer(mlp_size[i], mlp_size[i+1]) for i in range(len(nouts))]

    def __call__(self, x):

        for layer in self.layers:
            x = layer(x)
        return x


    def parameters(self):
        return [out for layer in self.layers for out in layer.parameters()]
