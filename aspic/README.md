# Description

This is an Answer Set Programms to Picat transpiler (source to source translator).

The transpiler is described in a paper accepted at ICLP 2026.

# How to use

## a) Using a convenience script

picat -log aspic.pi ASPFILE1.lp ASPFILE2.lp

## b) or with explicit calls:

picat -log aspic_transpiler.pi ASPFILE.lp 2>tmpfile.pi

picat -log tmpfile.pi 2>&1

## c) or using an alias:

It is convenient to define an alias
```
alias aspic="picat -log aspic.pi "
```
and then use: aspic ASPFILE.lp 

The examples below assume this alias. Otherwise just replace manually
"aspic" with "picat -log aspic.pi" in the examples.

# Choice between cp and sat

Picat can use multiple libraries for solving constraint models. Aspic
supports now sat (default, being usually the fastest) 
and cp (much faster for selected problems like the jobshop scheduling).

To specify one of those just use it as the first argument to aspic, before
the list of lp files.

```
aspic sat ASPFILE.lp
aspic cp ASPFILE.lp
```

# Generating all solutions:

To generate all solutions, instead of a single one, add "all" when calling ASPIC:

```
# all solutions, using sat
aspic all ASPFILE.lp

#all solutions, with explicit choice of the constraints library
aspic sat/all ASPFILE.lp
aspic cp/all ASPFILE.lp

```


# Show
The annotation #show is not yet implemented, 
instead you can use the script show, like this

aspic ASPFILE.lp | grep solution | ./show predicate

where predicate is the one you are interested in.

Complete example:
```
$ picat -log aspic.pi examples/hk_coloring.lp 2>&1|grep solution|./show color/2
color(belgium,white)
color(denmark,white)
color(france,green)
color(germany,blue)
color(luxembourg,red)
color(netherlands,green)
```


# Not implemented yet:

- several language aspects: explicit #count, #sum, #max, #min, #show 

- probably others as well

# Requirements

- you do have Picat installed (tested with 3.9)

- for the optional script "show", one needs to have python3 installed 

- sed needs to be in the path

- so far only tested on Linux 

# News

- Initial optimization support addded (#minimize)

- One can choose between sat (default) and cp

- It is possible now to call aspic with multiple ASP source files
