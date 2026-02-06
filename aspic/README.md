# Description

This is an Answer Set Programms to Picat transpiler (source to source translator).

The transpiler is described in a paper sent to ICLP 2026.

# How to use

## a) Using a convenience script

picat -log aspic.pi ASPFILE.lp

## b) or with explicit calls:

picat -log aspic_transpiler.pi ASPFILE.lp 2>tmpfile.pi

picat -log tmpfile.pi 2>&1

# Show
The annotation #show is not yet implemented, 
instead you can use the script show, like this

picat -log aspic.pi ASPFILE.lp | grep solution | ./show predicate

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

# Generating all solutions:

To generate all solutions, instead of a single one, add "all" when calling ASPIC:

```
picat -log aspic.pi ASPFILE.lp all
```

# Not implemented yet:

* Optimization support

# Requirements

- you do have picat installed (tested with 3.9)

- for the optional script "show", one needs to have python3 installed 

