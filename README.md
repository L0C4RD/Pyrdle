# Pyrdle
A pure-Python Wordle and Absurdle solver

Find the originals here:

 - [Wordle](https://www.powerlanguage.co.uk/wordle/)
 - [Absurdle](https://qntm.org/files/absurdle/absurdle.html)

## Basic solving: Wordle
To solve today's Wordle, simply run:

```
./pyrdle.py -w
```

## Basic solving: Absurdle
To solve Absurdle, simply run:

```
./pyrdle.py -s
```

To find a more optimal solution using a slower branch-pruning algorithm, run:

```
./pyrdle.py -s -p
```

You can also use the `-n` flag with branch pruning to control the number of unpruned branches (the default is 20, but you should be able to go as low as 6 without producing suboptimal solutions):

```
./pyrdle.py -s -p -n 6
```

To solve Absurdle's challenge mode, simply enter the target word as a final argument:

```
./pyrdle.py -s AZURE
```

## Play Absurdle

To play an offline version of Absurdle, simply run:

```
./pyrdle.py
```

You can also play Absurdle's challenge mode by providing the `-c` option:

```
./pyrdle.py -c
```
