# -*- coding: utf-8 -*-

r"""
This module implements solver objects who minimize an objective function. Call
:func:`solve` to solve your convex optimization problem using your instanced
solver and functions objects. The :class:`solver` base class defines the
interface of all solver object. The specialized solver objects inherit from it
and implement the class methods. The following solvers are included :

* :class:`forward_backward`: forward-backward proximal splitting algorithm
"""

import numpy as np
import time


def solve(solver, f1, f2, x0, relTol=10**-3, absTol=float('-inf'),
          convergence_speed=float('-inf'), maxIter=200, verbosity='low'):
    r"""
    This function solves an optimization problem whose objective function is
    the sum of two convex functions.

    This function minimizes the objective function
    :math:`f(x) = f_1(x) + f_2(x)`, i.e. solves
    :math:`\arg\!\min_x f_1(x) + f_2(x)` for
    :math:`x \in \mathbb{R}^N` using whatever algorithm.
    Returns a dictionary with the solution and some informations about
    the algorithm execution.

    Parameters
    ----------
    solver : solver object
        the solver algorithm. It is an object who must implement the
        :meth:`pyunlocbox.solvers.solver.pre`,
        :meth:`pyunlocbox.solvers.solver.algo` and
        :meth:`pyunlocbox.solvers.solver.post` methods.
    f1 : func class instance
        first convex function to minimize. It is an object who must implement
        the :meth:`pyunlocbox.functions.func.eval` method. The
        :meth:`pyunlocbox.functions.func.grad` and / or
        :meth:`pyunlocbox.functions.func.prox` methods are required by some
        solvers. Please refer to the documentation of the considered solver.
    f2 : func class instance
        second convex function to minimize, with a :math:`\beta` Lipschitz
        continuous gradient. It is an object who must implement the
        :meth:`pyunlocbox.functions.func.eval` method. The
        :meth:`pyunlocbox.functions.func.grad` and / or
        :meth:`pyunlocbox.functions.func.prox` methods are required by some
        solvers. Please refer to the documentation of the considered solver.
    x0 : array_like
        starting point of the algorithm, :math:`x_0 \in \mathbb{R}^N`
    relTol : float, optional
        The convergence (relative tolerance) stopping criterion. The algorithm
        stops if :math:`\frac{n(k)-n(k-1)}{n(k)}<reltol` where
        :math:`n(k)=f(x)=f_1(x)+f_2(x)` is the objective function at iteration
        :math:`k`. Default is :math:`10^{-3}`.
    absTol : float, optional
        the absolute tolerance stopping criterion. The algorithm stops if
        :math:`n(k)<abstol`. Default is minus infinity.
    convergence_speed : float, optional
        The minimum tolerable convergence speed of the objective function. The
        algorithm stops if n(k-1) - n(k) < `convergence_speed`. Default is
        minus infinity (i.e. the objective function may even increase).
    maxIter : int, optional
        the maximum number of iterations. Default is 200.
    verbosity : {'low', 'high', 'none'}, optional
        The log level : 'none' for no log, 'low' to print main steps, 'high' to
        print all steps. Default is 'low'.

    Returns
    -------
    sol : ndarray
        solution
    algo : str
        used algorithm
    niter : int
        number of iterations
    time : float
        execution time in seconds
    eval : float
        final evaluation of the objective function :math:`f(x)`
    crit : {'MAX_IT', 'ABS_TOL', 'REL_TOL', 'CONV_SPEED'}
        Used stopping criterion. 'MAX_IT' if the maximum number of iterations
        `maxIter` is reached, 'ABS_TOL' if the objective function value is
        smaller than `absTol`, 'REL_TOL' if the relative objective function
        improvement was smaller than `relTol` (i.e. the algorithm converged),
        'CONV_SPEED' if the objective function improvement is smaller than
        `convergence_speed`.
    rel : float
        relative objective improvement at convergence
    objective : ndarray
        successive evaluations of the objective function at each iteration

    Examples
    --------

    Basic example :

    >>> import pyunlocbox
    >>> solver1 = pyunlocbox.solvers.forward_backward('FISTA', gamma=2)
    >>> f1 = None
    >>> f2 = None
    >>> x0 = None
    >>> sol, info, objective = pyunlocbox.solvers.solve(solver1, f1, f2, x0)
    0
    """

    # Common initialization.
    if relTol < 0 or absTol < 0 or maxIter < 0:
        raise ValueError('Parameters should be positive numbers.')
    if verbosity not in ['none', 'low', 'high']:
        raise ValueError('Verbosity should be either none, low or high.')

    startTime = time.time()
    objective = [f1.eval(x0) + f2.eval(x0)]
    stopCrit = None
    nIter = 0

    # Solver specific initialization.
    solver.pre(x0, verbosity)

    while not stopCrit:

        nIter += 1

        # Solver iterative algorithm.
        solver.algo(f1, f2, verbosity)

        objective.append(f1.eval(solver.sol) + f2.eval(solver.sol))

        if objective[-1] == 0:
            if verbosity in ['low', 'high']:
                print('WARNING: objective function is equal to 0 ! '
                      'Adding some epsilon to continue.')
            # np.spacing(1.0) is equivalent to matlab eps = eps(1.0)
            objective[-1] = np.spacing(1.0)

        relative = abs((objective[-1] - objective[-2]) / objective[-1])

        # Verify stopping criteria.
        if objective[-1] < absTol:
            stopCrit = 'ABS_TOL'
        elif relative < relTol:
            stopCrit = 'REL_TOL'
        elif nIter >= maxIter:
            stopCrit = 'MAX_IT'
        elif objective[-2] - objective[-1] < convergence_speed:
            stopCrit = 'CONV_SPEED'

# post process
        if verbosity == 'high':
            print('Iteration %d : objective = %f, relative = %f'
                  % (nIter, objective[-1], relative))

    # Solver specific post-processing.
    solver.post(verbosity)

    if verbosity in ['high', 'low']:
        print('Solution found in %d iterations :' % (nIter))
        print('\tobjective function f(sol) = %f' % (objective[-1]))
        print('\trelative objective last improvement : %f' % (relative))
        print('\tstopping criterion : %s' % (stopCrit))

    # Returned dictionary.
    result = {'sol':       solver.sol,
              'algo':      solver.__class__.__name__,
              'niter':     nIter,
              'time':      time.time() - startTime,
              'eval':      objective[-1],
              'objective': objective,
              'crit':      stopCrit,
              'rel':       relative}

    return result


class solver(object):
    r"""
    This class defines the solver object interface.

    This class defines the interface of a solver object intended to be passed
    to the :func:`pyunlocbox.solvers.solve` solving function. It is intended to
    be a base class for standard solvers which will implement the required
    methods. It can also be instantiated by user code and dynamically modified
    for rapid testing. This class also defines the generic attributes of all
    solver objects.

    Parameters
    ----------
    gamma : float
        the step size. This parameter is upper bounded by
        :math:`\frac{1}{\beta}` where :math:`f_2` is :math:`\beta` Lipschitz
        continuous. Default is 1.
    """

    def __init__(self, gamma=1):
        if gamma < 0:
            raise ValueError('Gamma should be a positive number.')
        self.gamma = gamma

    def pre(self, x0, verbosity):
        """
        Solver specific initialization. See parameters documentation in
        :func:`pyunlocbox.solvers.solve` documentation.
        """
        raise NotImplementedError("Class user should define this method.")

    def algo(self, f1, f2, verbosity):
        """
        Solver iterative algorithm. See parameters documentation in
        :func:`pyunlocbox.solvers.solve` documentation.
        """
        raise NotImplementedError("Class user should define this method.")

    def post(self, verbosity):
        """
        Solver specific post-processing. See parameters documentation in
        :func:`pyunlocbox.solvers.solve` documentation.
        """
        raise NotImplementedError("Class user should define this method.")


class forward_backward(solver):
    r"""
    Forward-backward proximal splitting algorithm.

    See generic attributes descriptions of the
    :class:`pyunlocbox.solvers.solver` base class.

    Parameters
    ----------
    method : {'FISTA', 'ISTA'}, optional
        the method used to solve the problem.  It can be 'FISTA' or 'ISTA'.
        Default is 'FISTA'.
    lamb : float, optional
        the update term weight for ISTA.  It should be between 0 and 1. Default
        is 1.

    Notes
    -----
    This algorithm requires `f1` to implement the
    :meth:`pyunlocbox.functions.func.prox` method and `f2` to implement the
    :meth:`pyunlocbox.functions.func.grad` method.

    Examples
    --------
    >>> import pyunlocbox
    >>> solver1 = pyunlocbox.solvers.forward_backward('FISTA', gamma=2)
    >>> f1 = None
    >>> f2 = None
    >>> x0 = None
    >>> sol = pyunlocbox.solvers.solve(solver1, f1, f2, x0)
    0
    """

    def __init__(self, method='FISTA', lamb=1, *args, **kwargs):

        solver.__init__(self, *args, **kwargs)

        if method not in ['FISTA', 'ISTA']:
            raise ValueError('The method should be FISTA or ISTA.')
        self.method = method

        if lamb < 0 or lamb > 1:
            raise ValueError('Lambda is bounded by 0 and 1.')
        self.lamb = lamb

    def pre(self, x0, verbosity):
        """
        Algorithm initialization.
        """
        if verbosity == 'high':
            print('Selected algorithm : %s' % (self.method))

        # ISTA and FISTA initialization.
        self.sol = np.array(x0)

        # FISTA initialization.
        self.un = np.array(x0)
        self.tn = 1.

    def algo(self, f1, f2, verbosity):
        """
        Iterative ISTA or FISTA algorithm.
        """
        if self.method == 'ISTA':
            yn = self.sol - self.gamma * f2.grad(self.sol)
            self.sol += self.lamb * (f1.prox(yn, self.gamma) - self.sol)
        elif self.method == 'FISTA':
            xn = f1.prox(self.un - self.gamma * f2.grad(self.un), self.gamma)
            tn1 = (1. + np.sqrt(1.+4.*self.tn**2.)) / 2.
            self.un = xn + (self.tn-1) / tn1 * (xn-self.sol)
            self.sol = xn
            self.tn = tn1
        else:
            raise ValueError('The method should be FISTA or ISTA.')

    def post(self, verbosity):
        """
        No post-processing.
        """
        pass
