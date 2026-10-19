
import math
class Value:

    def __init__(self, data, children =(), operator = ""):

        self.data = data
        self.children = set(children)
        self.operator = operator
        self.grad = 0
        self._backward = lambda : None
    
    def __repr__(self):
        return f"Value={self.data}"

    def __add__(self, other):
        other = other if isinstance(other, Value) else Value(other)
        output = Value(self.data + other.data, children=(self, other), operator="+")

        def _backward():
            self.grad += output.grad
            other.grad += output.grad
            
        output._backward = _backward
        return output

    def __radd__(self, other):
        return self + other

    def __sub__(self, other):
        return self + (-other)

    def __rsub__(self, other):
        return other + (-self)

    def exp(self):
        output = Value(math.exp(self.data), (self, ), "exp")

        def _backward():
            self.grad += output.data * output.grad # d(e*)dx = e**
        output._backward = _backward
        return output
    
    def tanh(self):
        x = self.data
        t = (math.exp(2*x) -1)/(math.exp(2*x) + 1)
        output = Value(t, (self, ), "tanh" )

        def _backward():
            self.grad += (1- t**2) * output.grad
        output._backward = _backward
        return output

    def __pow__(self, other):
        assert isinstance(other, (float, int))
        output = Value(self.data ** other, (self,), "**")

        def _backward():
            self.grad += other * (self.data ** (other -1)) * output.grad

        output._backward = _backward
        return output
    

    def __mul__(self, other):
        other = other if isinstance(other, Value) else Value(other)
        output = Value(self.data * other.data, children=(self, other), operator="*")

        def _backward():
            self.grad += other.data * output.grad
            other.grad += self.data * output.grad
        output._backward = _backward
        return output
    
    def __rmul__(self, other):
        return self * other

    def __neg__(self):
        return -1* self


    def __truediv__(self, other):
        return self * other**-1

    def __rtruediv__(self, other):
        return other * self**-1

    def backward(self):

        visited = set()
        sort_nodes = []

        def top_sort(current):
            if current not in visited:
                visited.add(current)
                for child in current.children:
                    top_sort(child)
                sort_nodes.append(current)
        top_sort(self)
        self.grad = 1
        for output in reversed(sort_nodes):
            output._backward()