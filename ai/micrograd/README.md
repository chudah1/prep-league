# Micrograd part 2

This folder contains a scalar autograd engine, neural-network building blocks,
and two manual training loops. Run them from the repository root:

```bash
python3 -m ai.micrograd.train_toy
python3 -m ai.micrograd.train_moons
python3 -m pytest -q ai/micrograd
```

## Results

- Toy final MSE: `0.019568` after 100 steps
- Moons final training accuracy: `97%` after 100 steps

The network `MLP(3, [4, 4, 1])` has 41 trainable scalar values:
`4 * (3 weights + 1 bias) + 4 * (4 weights + 1 bias) +
1 * (4 weights + 1 bias)`.
