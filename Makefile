CPP=gcc
CFLAGS=-Wall -fPIC
LDFLAGS=-lpthread

all: cmddemo_spi libled.so

cmddemo_spi: main.o spi.o file.o
	$(CPP) $(CFLAGS) main.o spi.o file.o -o cmddemo_spi $(LDFLAGS)

libled.so: led_shared.o spi.o file.o
	$(CPP) -shared $^ -o $@ $(LDFLAGS)

main.o: main.c spi.h file.h
	$(CPP) $(CFLAGS) -c main.c -o main.o

spi.o: spi.c spi.h
	$(CPP) $(CFLAGS) -c spi.c -o spi.o

file.o: file.c file.h
	$(CPP) $(CFLAGS) -c file.c -o file.o

led_shared.o: main.c spi.h file.h
	$(CPP) $(CFLAGS) -DBUILD_SHARED_LIB -c main.c -o led_shared.o

clean:
	$(RM) *.o cmddemo_spi libled.so