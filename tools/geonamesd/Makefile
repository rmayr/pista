kdlib = kdtree-0.5.6/libkdtree.a

CC = gcc
CFLAGS = -Wall -g -Ikdtree-0.5.6 -Itinycdb-0.78 -Imongoose
LDFLAGS = $(kdlib) -lm tinycdb-0.78/libcdb.a

all: geonamesd

geonamesd: geonamesd.c $(kdlib) mongoose.o
	gcc $(CFLAGS)  -o geonamesd geonamesd.c mongoose.o $(LDFLAGS) 

mongoose.o: mongoose/mongoose.c mongoose/mongoose.h
	$(CC) $(CFLAGS) -c mongoose/mongoose.c -o mongoose.o

clean:
	rm -f *.o
	rm -rf geonamesd.dSYM

clobber: clean
	rm -f geonamesd
