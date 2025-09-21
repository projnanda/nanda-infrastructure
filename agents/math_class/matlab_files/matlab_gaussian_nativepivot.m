% Source: https://www.mathworks.com/matlabcentral/fileexchange/110900-step-by-step-gaussian-elimination-method?s_tid=FX_rc3_behav
% Gaussian elimination directly on the augmented matrix M = [A | B]

function M = matlab_gaussian_nativepivot(M)
    % Matrix Dimensions
    [m,n] = size(M);
    % Loop over pivot columns
    for j = 1:m-1
        % Pivot
        for z = j+1:m
            % If pivot element M(i,j) is zero, swap with lower row
            if M(j,j) == 0
                disp("replace row" + j + " with row" + z);
                tmp = M(j,:);
                M(j,:) = M(z,:);
                M(z,:) = tmp;
            end
        end
        % Eliminate entries below the pivot
        for i = j+1:m
            disp("Eliminate M(" + i + "," + j + ")");
            M(i,:) = M(i,:) - M(j,:)*(M(i,j)/M(j,j));
        end
    end
end
