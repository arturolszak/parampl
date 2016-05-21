option solver knitro;
param xmin:=-60;
param xmax:=60;
param n:=200;
param p:=10;
param xmin1;
param xmax1;
param dx;
param est_czas_rown;
param est_czas_sekw;
param liczba_min_lok;
param czasy{1..p};
var  x{1..n}  >= xmin <= xmax;
var  fi{i in 1..n}=n-(sum{j in 1..n}cos(x[j]))+i*(1-cos(x[i]))-sin(x[i]); 
minimize f: sum{i in 1..n} fi[i]^2;
subject to cons1:
xmin1 <= x[1] <= xmax1;
for{j in 1..p}{
   let liczba_min_lok:=0;
   printf "\n\n-- Liczba podzadan: %d --:\n", j;
   let dx:=(xmax-xmin)/j;
   for{k in 1..j}{
      printf "\n\n-- Podzadanie: %d --:\n", k;
      let xmin1:=xmin+(k-1)*dx;
      let xmax1:=xmin1+dx;
      solve;
      if abs(f) < 1.e-4 then let liczba_min_lok:=liczba_min_lok+1;
#      display x;
      display _solve_time;
      let czasy[k]:=_solve_time;
   }
      let est_czas_sekw:=sum{i in 1..j}  czasy[i];
      let est_czas_rown:=max{i in 1..j}  czasy[i];
      printf "\n\n-- Estymata przyspieszenia dzieki zrown.: %f --\n \n", est_czas_sekw/est_czas_rown;
      printf "-- Znalezionych minimow lokalnych: %d --\n", liczba_min_lok; 
      printf "\n\n-- ================= ";
}
   
