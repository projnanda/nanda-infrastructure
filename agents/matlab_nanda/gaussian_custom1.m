function [x, Ab, steps] = gaussian_custom1(A, b)
    A = double(A); b = double(b(:));
    [n,m] = size(A); if n~=m, error('A must be square'); end
    if numel(b)~=n, error('b length mismatch'); end
    Ab = [A b]; steps = strings(0,1);
    for k=1:n-1
        [~,pivRel]=max(abs(Ab(k:n,k))); piv=pivRel+k-1;
        if Ab(piv,k)~=0 && piv~=k, Ab([k,piv],:)=Ab([piv,k],:); steps(end+1)=sprintf('R%d <-> R%d',k,piv); end
        if Ab(k,k)==0, continue; end
        for i=k+1:n
            m=Ab(i,k)/Ab(k,k); Ab(i,k:end)=Ab(i,k:end)-m*Ab(k,k:end);
            steps(end+1)=sprintf('R%d = R%d - (%.6g) R%d',i,i,m,k);
        end
    end
    x=zeros(n,1);
    for i=n:-1:1
        if Ab(i,i)==0, if abs(Ab(i,end))<1e-12, x(i)=0; else, error('Inconsistent'); end
        else, x(i)=(Ab(i,end)-Ab(i,i+1:n)*x(i+1:n))/Ab(i,i); end
    end
end
