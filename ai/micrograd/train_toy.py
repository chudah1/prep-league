
import random

from engine import Value
from nn import MLP


INPUTS = [
    [2.0, 3.0, -1.0],
    [3.0, -1.0, 0.5],
    [0.5, 1.0, 1.0],
    [1.0, 1.0, -1.0],
]
TARGETS = [1.0, -1.0, -1.0, 1.0]


def train(steps: int = 100, learning_rate: float = 0.05) -> tuple[MLP, float]:
    random.seed(42)

    model = MLP(3, [4, 4, 1])

    loss = Value(0.0)
    for step in range(steps):
        #forward
        preds = [model(x) for x in INPUTS]
        loss = sum((pred-target)**2 for (pred, target) in zip(preds, TARGETS))/len(INPUTS)

        #backward
        for p in model.parameters():
            p.grad = 0 #zero grad
        loss.backward()
        #descent
        for p in model.parameters():
            p.data -= learning_rate * p.grad

        if step%10 == 0:
            print(f"loss:{loss}")

    return model, loss.data


if __name__ == "__main__":
    train()
