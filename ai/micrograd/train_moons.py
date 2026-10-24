"""Train the local MLP to separate the two-moons dataset."""

import random

from sklearn.datasets import make_moons
from nn import MLP
from engine import Value
features, labels = make_moons(n_samples=100, noise=0.1, random_state=42)
labels = labels * 2-1 #map back
print(features.shape)
print(labels.shape)
print(set(labels))

print(features[0], labels[0])

def train(steps:int = 100, learning_rate= 0.05):
    model = MLP(2, [16, 16, 1])
    for step in range(steps):
        loss = Value(0.0)

        #forward pass
        predictions =[model(example) for example in features]

        #loss
        loss = sum(((pred-target)**2 for pred, target in zip(predictions, labels)))/len(labels)


        for p in model.parameters():
            p.grad = 0.0 # zero grad
        
        loss.backward()

        #update (gradient_Descent)
        for p in model.parameters():
            p.data -= learning_rate * p.grad

        accuracy = sum((pred.data>0) == (label > 0) for pred, label in zip(predictions, labels))/len(labels)
        if step % 10 == 0:
            print(f"step {step}: loss={loss.data:.6f}")
            print(f"accuracy{accuracy:.1%}")

    final_predictions = [
        model(example)
        for example in features
    ]
    final_accuracy = sum(
        (prediction.data > 0) == (label > 0)
        for prediction, label in zip(final_predictions, labels)
    ) / len(labels)

    print(f"final training accuracy: {final_accuracy:.1%}")


if __name__ == "__main__":
    train()