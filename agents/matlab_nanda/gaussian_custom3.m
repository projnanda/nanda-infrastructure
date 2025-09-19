// Source: https://www.mathworks.com/matlabcentral/fileexchange/110900-step-by-step-gaussian-elimination-method?s_tid=FX_rc3_behav
function M = gaussian_custom3(M)
    [m,n] = size(M);
    for j = 1:m-1
        for z = j+1:m
            if M(j,j) == 0
                disp("replace row" + j + " with row" + z);
                tmp = M(j,:); 
                M(j,:) = M(z,:); 
                M(z,:) = tmp;
            end
        end
        for i = j+1:m
            disp("Eliminate M(" + i + "," + j + ")");
            M(i,:) = M(i,:) - M(j,:)*(M(i,j)/M(j,j));
        end
    end
end
