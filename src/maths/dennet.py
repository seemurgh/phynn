import torch
import torch.nn as nn
import torchdiffeq
import pytorch_lightning as pl
from src.maths.diffeq import DiffEq
from src.maths.diffeq_1DWave import Diffeq1DWave


class DENNet(pl.LightningModule):
    """
    A class to handle lower-level parameters of a differential equation neural network.
    This class inherits from PyTorch-Lightning.
    """

    def __init__(self, func: nn.Module, order=1, sensitivity='autograd', s_span=torch.linspace(0, 1, 2), solver='rk4',
                 atol=1e-4, rtol=1e-4, case='springmass'):
        super().__init__()

        # have an if for DiffEq of PDEeq
        if case == 'springmass':
            self.de_function = DiffEq(func, order)
        elif case == '1DWave':
            self.de_function = Diffeq1DWave(func, order)
        else:
            print('case named {} is not applied'.format(case))

        self.order = order
        self.sensitivity = sensitivity
        self.t_span = s_span
        self.solver = solver
        self.nfe = self.de_function.nfe
        self.rtol = rtol
        self.atol = atol
        self.case = case

    def _prep_odeint(self, x: torch.Tensor):
        self.t_span = self.t_span.to(x)

        # TODO handle other named_modules

        return x

    def forward(self, x: torch.Tensor):
        # not being used atm
        x = self._prep_odeint(x)
        switcher = {
            'autograd': self._autograd,
            'adjoint': self._adjoint,
        }
        odeint = switcher.get(self.sensitivity)
        out = odeint(x)
        return out

    def trajectory(self, x: torch.Tensor, s_span: torch.Tensor):
        x = self._prep_odeint(x)
        sol = torchdiffeq.odeint(self.de_function, x, s_span,
                                 rtol=self.rtol, atol=self.atol, method=self.solver)
        return sol

    def reset(self):
        self.nfe, self.de_function.nfe = 0, 0

    def _autograd(self, x):
        self.de_function.sensitivity = self.sensitivity

        return torchdiffeq.odeint(self.de_function, x, self.t_span, rtol=self.rtol, atol=self.atol,
                                  method=self.solver)[-1]

    @property
    def nfe(self):
        return self.de_function.nfe

    @nfe.setter
    def nfe(self, val):
        self.de_function.nfe = val
