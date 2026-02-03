% https://potassco.org/clingo/run/?example

% reached doesn't work without stable sets (evidence for "reached")
% in particular min(~"asp") mode does produce several disjoint cycles

% Nodes
node(1..2).
% (Directed) Edges
%edge(1,2).  edge(2,1).  
edge(X,Y)<=> &ismember((X,Y),[(1,2),(2,1)])&.
% Generate
{ cycle(X,Y) : edge(X,Y) } = 1 :- node(X).
{ cycle(X,Y) : edge(X,Y) } = 1 :- node(Y).
% Define
reached(Y) <=> cycle(1,Y);cycle(X,Y),reached(X).
% Test
:- node(Y), not reached(Y).
:-cycle(1,1).
%:-cycle(2,2).
%:-edge(2,2).


