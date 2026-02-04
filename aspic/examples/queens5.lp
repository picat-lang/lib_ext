% from https://potassco.org/clingo/run/?example
% aspic
% times with completion
% 128 1.2 s
% 256 6.7 s
% 512 30 s
% 768 20 m
% 1024 55 m 14s

#const n = 4.


% n-Queens encoding

{ q(I,1..n) } == 1 :- I = 1..n.
{ q(1..n,J) } == 1 :- J = 1..n.
:- { q(D-J,J) } >= 2, D = 2..2*n.
:- { q(D+J,J) } >= 2, D = 1-n..n-1.
