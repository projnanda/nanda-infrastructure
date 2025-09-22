function out = safe_calculator(expr)
% Evaluate basic numeric expressions safely in MATLAB.
% Supports + - * / ^ ( ) [ ] , ; : elementwise (.*, ./, .^), and funcs below.

arguments
    expr (1,1) string
end

allowed = ["sin","cos","tan","asin","acos","atan", ...
    "sqrt","exp","log","log10","abs","round","floor","ceil", ...
    "mod","rem","sum","mean","min","max", ...
    "bin2dec","hex2dec","dec2bin","dec2hex"]; 

t = strtrim(expr);

% Any identifiers must be whitelisted
ids = regexp(t, "[A-Za-z_]\w*", "match");
if ~isempty(ids)
    bad = setdiff(string(ids), allowed);
    if ~isempty(bad)
        error("safe_calculator:DisallowedToken", ...
            "Disallowed token(s): %s", strjoin(bad, ", "));
    end
end

% Allowed characters: digits, whitespace, ops, brackets, E/e, quotes, letters/underscore
if isempty(regexp(t, "^[0-9.\s+\-*/^()\[\],:;eE'A-Za-z_]+$", "once"))
    error("safe_calculator:BadChars", "Expression contains invalid characters.");
end

% Numeric evaluation
out = eval(t);
end
