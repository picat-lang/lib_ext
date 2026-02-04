% very fast ASP n-queens, personal communication Prof. Torsten Schaub
% not that fast yet with ASPIC
% slightly modified, to avoid arithmetics in clauses head
% explicit parantheses to workaround the parsing issues in arithmetic expressions
#const n=4.
{numbers(1..n*2-1)}. %populate the universe
{ queen(I,1..n) } = 1 :- I = 1..n.
{ queen(1..n,J) } = 1 :- J = 1..n.

 :- { queen(I,J) : d1(I,J,D) } > 1, D=1..n*2-1.
 :- { queen(I,J) : d2(I,J,D) } > 1, D=1..n*2-1.

d1(I,J,K) :- I = 1..n, J = 1..n, K=(I-J)+n.
d2(I,J,K) :- I = 1..n, J = 1..n, K=(I+J)-1.

#show queen/2.
