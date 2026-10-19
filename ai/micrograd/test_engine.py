from micrograd.engine import Value
import torch
import math



def test_value_impl_matches_pytorch():
    x1= Value(2.0)
    x2 = Value(0.0)


    w1 = Value(-3.0)
    w2 = Value(1.0)

    b =Value(6.881373587019543)

    x1w1x2w2 = (x1*w1 + x2*w2 + b).tanh()
    x1w1x2w2.backward()
    tx1 = torch.tensor(2.0, requires_grad=True)
    tx2 = torch.tensor(0.0, requires_grad=True)
    tw1 = torch.tensor(-3.0, requires_grad=True)
    tw2 = torch.tensor(1.0, requires_grad=True)
    tb = torch.tensor(6.881373587019543, requires_grad=True)

    torch_out = torch.tanh(tx1*tw1 + tx2 *tw2 + tb)
    torch_out.backward()

    for value, torch_vals in [
        (x1, tx1),
        (x2, tx2),
        (w1, tw1),
        (w2, tw2),
        (b, tb),
    ]:
        assert math.isclose(value.grad, torch_vals.grad.item(),  abs_tol=1e-6)


def test_gradient_accumulates_when_value_is_reused():
        a = Value(3.0)
        output = a + a

        output.backward()

        assert a.grad == 2.0