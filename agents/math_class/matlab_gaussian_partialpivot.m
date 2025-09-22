% Solve a linear system Ax = b using Gaussian Elimination with partial pivoting.
% Then, output the elimination steps and solution vector.

% A recreation of MATLAB's built-in mldivide (A\b)

function [x, Ab, steps] = matlab_gaussian_partialpivot(A, b)
% Inputs as Double precision
A = double(A);
b = double(b(:));

% Matrix dimensions
[n, m] = size(A);
if n ~= m
    error('A must be square');
end
if numel(b) ~= n
    error('b length mismatch');
end

% Augmented Matrix [A | b]
Ab = [A b];
steps = strings(0, 1);

% Elimination
for k = 1:n-1
    % Pivot
    [~, pivRel] = max(abs(Ab(k:n, k)));
    piv = pivRel + k - 1;

    % If necessary, swap rows
    if Ab(piv, k) ~= 0 && piv ~= k
        Ab([k, piv], :) = Ab([piv, k], :);
        steps(end+1) = sprintf('R%d <-> R%d', k, piv);
    end

    % If pivot is zero, skip
    if Ab(k, k) == 0
        continue;
    end

    % Eliminate entries below pivot
    for i = k+1:n
        m = Ab(i, k) / Ab(k, k);
        Ab(i, k:end) = Ab(i, k:end) - m * Ab(k, k:end);
        steps(end+1) = sprintf('R%d = R%d - (%.6g) R%d', i, i, m, k);
    end
end

% Back substitution
x = zeros(n, 1);
for i = n:-1:1
    if Ab(i, i) == 0
        if abs(Ab(i, end)) < 1e-12
            x(i) = 0;
        else
            error('Inconsistent');
        end
    else
        x(i) = (Ab(i, end) - Ab(i, i+1:n) * x(i+1:n)) / Ab(i, i);
    end
end
end
