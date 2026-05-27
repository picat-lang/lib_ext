%how to use global constraints from Picat
#const num=5.
univ(1..num).
{e(X,Y):X!=Y}.
&cond((N=5,V=[{I,1}:I_in_1..N],E=[{I,J,e(I,J)}:I_in_1..N,J_in_1..N],tree(V,E)),1,0)&.

