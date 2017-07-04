/**
* @brief Código - Comunicación con el módulo VS1003
*
* Comunicación a través de SPI con el módulo VS1003. Usamos el SPI para configurar
* el módulo y para enviarle datos que pueda descodificar.
*
* @file mp3_decoder.c
* @version 2.5
* @author David González Filoso <dgfiloso@b105.upm.es>
* @company B105 - Electronic Systems Lab
*/

#include "simba.h"
#include "mp3_decoder.h"

//VS10xx SCI Registers
#define SCI_MODE 0x00
#define SCI_STATUS 0x01
#define SCI_BASS 0x02
#define SCI_CLOCKF 0x03
#define SCI_DECODE_TIME 0x04
#define SCI_AUDATA 0x05
#define SCI_WRAM 0x06
#define SCI_WRAMADDR 0x07
#define SCI_HDAT0 0x08
#define SCI_HDAT1 0x09
#define SCI_AIADDR 0x0A
#define SCI_VOL 0x0B
#define SCI_AICTRL0 0x0C
#define SCI_AICTRL1 0x0D
#define SCI_AICTRL2 0x0E
#define SCI_AICTRL3 0x0F

/*  Global variables ----------------------------------------------------------------------------*/
static struct spi_driver_t spi;
static struct pin_driver_t dreq;
static struct pin_driver_t xcs;
static struct pin_driver_t xdcs;
static struct pin_driver_t xrst;

/*  Private functions prototypes ----------------------------------------------------------------*/

//  Escribe un valor en un registro del VS1003
void Mp3WriteRegister(unsigned char addressbyte, unsigned char highbyte, unsigned char lowbyte);

//  Resta tiempos utilizando estructuras de tipo time_t
void time_sub(struct time_t* res, struct time_t* left, struct time_t* right);

/*  Public functions ---------------------------------------------------------------------------*/

/**
 *  @brief  Configura el módulo Mp3 VS1003
 *
 *  Inicia el SPI del ESP8266 indicando que se va a usar el bus SPI 0 y que va a funcionar como maestro.
 *  También se indica que se va a transmitir a 8Mbps y los pines que se van a usar para controlar el módulo.
 *  Estos pines son los que necesita el módulo, DREQ indica si la FiFo esta llena, XRST resetea el módulo,
 *  XCS es el chip select para mandar comandos al módulo y XDCS es el chip select para mandar datos.
 *
 *  @param void
 *  @return void
 */
void configureMp3(void)
{
  struct time_t curr_time;
  struct time_t delay;

  if (spi_module_init() != 0)
  {
    std_printf("#Error: Cannot Initialize SPI");
    return;
  }

  spi_init(&spi, &spi_device[0], &pin_d7_dev, SPI_MODE_MASTER, SPI_SPEED_8MBPS, 1, 1);
  spi_start(&spi);

  pin_init(&dreq, &pin_d5_dev, PIN_INPUT);
  pin_init(&xcs, &pin_d2_dev, PIN_OUTPUT);
  pin_init(&xdcs, &pin_d4_dev, PIN_OUTPUT);
  pin_init(&xrst, &pin_d6_dev, PIN_OUTPUT);

  pin_write(&xrst, 0);
  pin_write(&xcs, 1);
  pin_write(&xdcs, 1);

  //  delay(1000);
  if (time_get(&curr_time) != 0)
  {
    std_printf("#ERROR: Cannot Get Current Time");
  }
  if (time_get(&delay) != 0)
  {
    std_printf("#ERROR: Cannot Get Current Time");
  }
  time_sub(&delay, &delay, &curr_time);
  while (delay.seconds < 1)
  {
    if (time_get(&delay) != 0)
    {
      std_printf("#ERROR: Cannot Get Current Time");
    }
    time_sub(&delay, &delay, &curr_time);
  }

  pin_write(&xrst, 0);

  //  delay(1000);
  if (time_get(&curr_time) != 0)
  {
    std_printf("#ERROR: Cannot Get Current Time");
  }
  if (time_get(&delay) != 0)
  {
    std_printf("#ERROR: Cannot Get Current Time");
  }
  time_sub(&delay, &delay, &curr_time);
  while (delay.seconds < 1)
  {
    if (time_get(&delay) != 0)
    {
      std_printf("#ERROR: Cannot Get Current Time");
    }
    time_sub(&delay, &delay, &curr_time);
  }

	Mp3WriteRegister(SCI_MODE, 0x08, 0x0C);

	Mp3WriteRegister(SCI_VOL, 0x00, 0x00);
	Mp3WriteRegister(SCI_CLOCKF, 0x60, 0x00);
}

/**
 *  @brief Envía datos al descodificador por SPI
 *
 *  Toma un buffer de datos y los va transmisitiendo de 32 bytes en 32 bytes al módulo VS1003
 *
 *  @param buf_p Puntero a un buffer de bytes
 *  @param size Tamaño del buffer
 *  @return void
 */
void sendMp3(uint8_t* buf_p, size_t size)
{
  uint8_t* buff;
  int i, j, num;
  int buff_size;

  buff = (uint8_t*)malloc(32*sizeof(uint8_t));
  num = (size + 32 -1)/32;

  for (i=0; i<num; i++)
  {
    if ((size - i*32) < 32)
    {
      buff_size = size - i*32;
    }
    else
    {
      buff_size = 32;
    }
    for (j=0; j<buff_size; j++)
    {
      *(buff+j) = *(buf_p + i*32 + j);
    }

    while(!pin_read(&dreq)) ; //Wait for DREQ to go high indicating IC is available
    pin_write(&xdcs, 0); //Select data
    if (spi_write(&spi, buff, buff_size) != buff_size)
    {
      std_printf("#ERROR: Cannot Write SPI Data");
    }
    pin_write(&xdcs, 1); //Deselect data
    while(!pin_read(&dreq)) ; //Wait for DREQ to go high indicating data is complete
  }
}

/*  Private functions --------------------------------------------------------------------------*/

/**
 *  @brief Configura un registro del módulo VS1003
 *
 *  @param addressbyte Dirección del registro de 16 bits que se quiere cambiar
 *  @param highbyte Byte alto que se quiere poner en el registro (bit 15 al 8)
 *  @param lowbyte Byte bajo que se quiere poner en el registro (bit 7 al 0)
 *  @return void
 */
void Mp3WriteRegister(unsigned char addressbyte, unsigned char highbyte, unsigned char lowbyte)
{
	char command[4];
	command[0] = 0x02;
	command[1] = addressbyte;
	command[2] = highbyte;
	command[3] = lowbyte;
  while(!pin_read(&dreq)) ; //Wait for DREQ to go high indicating IC is available

  pin_write(&xcs, 0); //Select control

  if (spi_write(&spi, command, 4) != 4)
  {
    std_printf("#ERROR: Cannot Write SPI Command");
  }

  pin_write(&xcs, 1); //Deselect Control

  while(!pin_read(&dreq)){
	 // printf("Register DREQ\r\n");
  } ; //Wait for DREQ to go high indicating command is complete
}

/**
 *  @brief Resta de tiempo
 *
 *  Resta tiempos a través de estructuras tipo time_t
 *
 *  @param res Puntero a struct time_t donde se guarda el resultado de la operación
 *  @param left Puntero a struct time_t que contiene el minuendo
 *  @param right Puntero a struct time_t que contiene el sustraendo
 *  @return void
 */
void time_sub(struct time_t* res, struct time_t* left, struct time_t* right)
{
  res->seconds = left->seconds - right->seconds;
  res->nanoseconds = left->nanoseconds - right->nanoseconds;
  if (res->nanoseconds < 0) {
    --res->seconds;
    res->nanoseconds += 1000000000;
}
}
