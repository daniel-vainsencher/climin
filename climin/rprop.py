# -*- coding: utf-8 -*-

"""This module contains the Resilient propagation optimizer."""



import mathadapt as ma

from base import Minimizer


class Rprop(Minimizer):
    """Rprop optimizer.

    Resilient propagation is an optimizer that was originally tailored towards
    neural networks. It can however be savely applied to all kinds of
    optimization problems.  The idea is to have a parameter specific step rate
    which is determined by sign changes of the derivative of the objective
    function.

    To be more precise, given the derivative of the loss given the parameters
    :math:`f'(\\theta_t)` at time step :math:`t`, the :math:`i` th component of
    the vector of steprates :math:`\\alpha` is determined as

    .. math::
       \\alpha_i \\leftarrow
       \\begin{cases}
           \\alpha_i \\cdot \\eta_{\\text{grow}} ~\\text{if}~ f'(\\theta_t)_i \\cdot f'(\\theta_{t-1})_i > 0 \\\\
           \\alpha_i \\cdot \\eta_{\\text{shrink}} ~\\text{if}~ f'(\\theta_t)_i \\cdot f'(\\theta_{t-1})_i < 0 \\\\
           \\alpha_i
       \\end{cases}

    where :math:`0 < \\eta_{\\text{shrink}} < 1 < \\eta_{\\text{grow}}`
    specifies the shrink and growth rates of the step rates. Typically, we will
    threshold the step rates at minimum and maximum values.

    The parameters are then adapted according to the sign of the error gradient:

    .. math::
       \\theta_{t+1} = -\\alpha~\\text{sgn}(f'(\\theta_t)).

    This results in a method which is quite robust. On the other hand, it is
    more sensitive towards stochastic objectives, since that stochasticity might
    lead to bad estimates of the sign of the gradient.

    .. note::
       Works with gnumpy.

    .. [riedmiller1992rprop] M. Riedmiller und Heinrich Braun: Rprop - A Fast
       Adaptive Learning Algorithm. Proceedings of the International Symposium
       on Computer and Information Science VII, 1992


    Attributes
    ----------
    wrt : array_like
        Current solution to the problem. Can be given as a first argument to \
        ``.fprime``.

    fprime : Callable
        First derivative of the objective function. Returns an array of the \
        same shape as ``.wrt``.

    step_shrink : float
        Constant to shrink step rates by if the gradients of the error do not
        agree over time.

    step_grow : float
        Constant to grow step rates by if the gradients of the error do
        agree over time.

    min_step : float
        Minimum step rate.

    max_step : float
        Maximum step rate.
    """

    def __init__(self, wrt, fprime, step_shrink=0.5, step_grow=1.2,
                 min_step=1E-6, max_step=1, changes_max=0.1, args=None):
        """Create an Rprop object.

        Parameters
        ----------

        wrt : array_like
            Current solution to the problem. Can be given as a first argument
            to ``.fprime``.

        fprime : Callable
            First derivative of the objective function. Returns an array of the
            same shape as ``.wrt``.

        step_shrink : float
            Constant to shrink step rates by if the gradients of the error do
            not agree over time.

        step_grow : float
            Constant to grow step rates by if the gradients of the error do
            agree over time.

        min_step : float
            Minimum step rate.

        max_step : float
            Maximum step rate.

        args : iterable
            Iterator over arguments which ``fprime`` will be called with.
        """
        super(Rprop, self).__init__(wrt, args=args)

        self.fprime = fprime
        self.step_shrink = step_shrink
        self.step_grow = step_grow
        self.min_step = min_step
        self.max_step = max_step
        self.changes_max = changes_max

    def __iter__(self):
        gradient_m1 = ma.zero_like(self.wrt)
        changes = ma.random_like(self.wrt) * self.changes_max

        for i, (args, kwargs) in enumerate(self.args):
            gradient = self.fprime(self.wrt, *args, **kwargs)
            changes_min = changes * self.step_grow
            changes_max = changes * self.step_shrink
            gradprod = gradient_m1 * gradient
            changes_min *= gradprod > 0
            changes_max *= gradprod < 0
            changes *= gradprod == 0

            # TODO actually, this should be done to changes
            changes_min = ma.clip(changes_min, self.min_step, self.max_step)
            changes_max = ma.clip(changes_max, self.min_step, self.max_step)

            changes += changes_min + changes_max
            step = -changes * ma.sign(gradient)
            self.wrt += step

            gradient_m1 = gradient

            yield {
                'n_iter': i,
                'args': args,
                'kwargs': kwargs,
                'gradient': gradient,
                'gradient_m1': gradient_m1,
                'step': step,
            }
