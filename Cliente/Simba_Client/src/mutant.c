/**
* @brief Código - Lógica de control con el servidor Cerebro y gestión del audio recibido.
*
* Utilizando una máquina de estados de tipo Mealy gestiona la conexión con el servidor
* Cerebro a través de Websocket. Diferencia entre texto o datos binarios recibidos, para
* gestionarlo como un comando del sistema o como datos que tiene que enviar al descodificador.
*
* @file mutant.c
* @version 2.4
* @author David González Filoso <dgfiloso@b105.upm.es>
* @company B105 - Electronic Systems Lab
**/

#include "simba.h"
#include "jsmn.h"
#include "mutant.h"

#define OPCODE_CONT   0x00
#define OPCODE_TEXT   0x01
#define OPCODE_BINARY 0x02
#define OPCODE_CLOSE  0x08
#define OPCODE_PING   0x09
#define OPCODE_PONG   0x0a

#define DATA_TEXT   0x01
#define DATA_BIN    0x02
#define DATA_UNDEF  0x04
#define RCV_TEXT    0x08
#define RCV_BIN     0x10

enum mutant_state {
  WAITING,
  DATA_TYPE,
  TEXT,
  BIN,
};

/*  Private functions prototypes --------------------------------*/
static int socket_data(fsm_t* this);
static int undef_data(fsm_t* this);
static int text_data(fsm_t* this);
static int bin_data(fsm_t* this);
static int data_rcv(fsm_t* this);
static void header_proc(fsm_t* this);
static void text_proc(fsm_t* this);
static void bin_proc(fsm_t* this);

/*  Global variables ------------------------------------------*/
static struct http_websocket_client_t mutant;
static uint8_t flags;
static uint64_t data_length;

//  Estados y transiciones de la máquina
static fsm_trans_t mutant_fsm[] = {
  { WAITING,    socket_data,  DATA_TYPE,  header_proc },
  { DATA_TYPE,  undef_data,   WAITING,    NULL        },
  { DATA_TYPE,  text_data,    TEXT,       NULL        },
  { DATA_TYPE,  bin_data,     BIN,        NULL        },
  { TEXT,       data_rcv,     WAITING,    text_proc   },
  { BIN,        data_rcv,     WAITING,    bin_proc    },
  {-1,          NULL,         -1,         NULL        }
};

/*  Public functions -------------------------------------------*/

/**
 *  @brief Crea una nueva estructura de máquina de estados
 *
 *  Llama a la función para crear una nueva máquina de estados, tomando como
 *  parámetro la tabla de transiciones.
 */
fsm_t* fsm_mutant_new(void)
{
  return fsm_new (mutant_fsm);
}

/**
 *  @brief  Devuelve la cantidad de datos recibidos por el socket TCP.
 *
 *  Hace uso del objeto cliente de Websocket para devolver la cantidad de bytes
 *  almacenados en la memoria de entrada del socket TCP.
 *
 *  @param void
 *  @return size_t Tamaño de los datos recibidos
 */
size_t rcv_socket_size(void)
{
  return mutant.server.socket.input.u.recvfrom.left;
}

/**
 *  @brief  Conexión del cliente al servidor Websocket
 *
 *  Primero inicializa el cliente de Websocket indicando la IP del servidor y
 *  el puerto. Después lo conecta al servidor.
 *
 *  @param  server_ip String que contiene la dirección IP del servidor
 *  @param  server_port Entero con el puerto en el que esta escuchando el servidor
 *  @return Devuelve 0 si no ha habido ningún problema, -1 si algo ha fallado
 */
int mutant_connect(const char *server_ip, const int server_port)
{
  int error;

  if (http_websocket_client_init(&mutant,server_ip,server_port,"/") != 0)
  {
    std_printf(OSTR("#ERROR: Websocket Cliente Init Failed\n"));
    return (-1);
  }

  if ((error = http_websocket_client_connect(&mutant)) != 0)
  {
    std_printf(OSTR("#ERROR: Websocket Connection Failed\n"));
    std_printf(OSTR("%d\n"), error);
    return (error);
  }
  return (0);
}

/*  Private functions ------------------------------------------------------*/

/**
 *  @brief  Función de cambio de estado, indica si se han recibido datos por el socket TCP.
 *
 *  Esta función devuelve 1 si el tamaño de los datos recibidos por el socket TCP es mayor de 0.
 *
 *  @param  this  Puntero a una máquina de estados
 *  @return int Entero que indica si se han recibido datos (1) o no (0)
 */
static int socket_data(fsm_t* this)
{
  if (rcv_socket_size() > 0)
  {
    return 1;
  }
  else
  {
    return 0;
  }
}

/**
 *  @brief  Función de cambio de estado que indica si los datos son de tipo desconocido.
 *
 *  Esta función devuelve un flag indicando si el tipo de datos es indefinido.
 *
 *  @param this Puntero a una máquina de estados
 *  @return int Indica si los datos son indefinidos (1)
 */
static int undef_data(fsm_t* this)
{
  int data;
  data = DATA_UNDEF & flags;
  flags &= ~DATA_UNDEF;
  return data;
}

/**
 *  @brief  Función de cambio de estado que indica si los datos son de tipo texto.
 *
 *  Esta función devuelve un flag indicando si el tipo de datos es texto.
 *
 *  @param this Puntero a una máquina de estados
 *  @return int Indica si los datos son texto (1)
 */
static int text_data(fsm_t* this)
{
  int data;
  data = DATA_TEXT & flags;
  flags &= ~DATA_TEXT;
  return data;
}

/**
 *  @brief  Función de cambio de estado que indica si los datos son de tipo binario.
 *
 *  Esta función devuelve un flag indicando si el tipo de datos es binario.
 *
 *  @param this Puntero a una máquina de estados
 *  @return int Indica si los datos son binarios (1)
 */
static int bin_data(fsm_t* this)
{
  int data;
  data = DATA_BIN & flags;
  flags &= ~DATA_BIN;
  return data;
}

/**
 *  @brief  Función de cambio de estado que indica salta si hay tantos
 *  datos como dice el campo de longitud.
 *
 *  Esta función salta si la cantidad de datos es mayor o igual a la indicada
 *  por el campo de longitud. Si es menor los lee y los descarta.
 *
 *  @param  this  Puntero a una máquina de estados
 *  @return int Indica si se han recibido la cantidad de datos indicados (1)
 */
static int data_rcv(fsm_t* this)
{
  uint8_t* temp;
  int i, socket_size;

  socket_size = rcv_socket_size();

  std_printf("%d %d\n", socket_size, data_length);
  if (socket_size >= data_length)
  {
    return 1;
  }
  else
  {
    temp = (uint8_t*)malloc(sizeof(uint8_t));
    for (i=0; i<socket_size; i++)
    {
      socket_read(&(mutant.server.socket), temp, sizeof(temp));
    }
    free(temp);
    return 0;
  }
}

/**
 *  @brief  Función de salida que procesa la cabecera de Websocket.
 *
 *  Lee la cabecera de Websocket para extraer el tipo de datos y la cantidad
 *  de los mismos que se han recibido. Para ello se leen los dos primeros bytes
 *  de los datos recibidos. Si el campo de longitud es 126 se leen dos bytes más,
 *  que indicarán la longitud de los datos. Si el campo de longitud es 127 se leen
 *  ocho bytes más, que indicarán la longitud de los datos. En el campo del tipo de
 *  datos sólo nos interesa si los datos son texto o binario, el resto lo consideramos
 *  indefinido.
 *
 *  @param  this  Puntero a una máquina de estados
 *  @return void
 */
static void header_proc(fsm_t* this)
{
  uint8_t header[8];
  uint8_t proc_header;
  uint64_t length0, length1, length2, length3, length4, length5, length6, length7;
  length0 = 0x0000000000000000;
  length1 = 0x0000000000000000;
  length2 = 0x0000000000000000;
  length3 = 0x0000000000000000;
  length4 = 0x0000000000000000;
  length5 = 0x0000000000000000;
  length6 = 0x0000000000000000;
  length7 = 0x0000000000000000;

  socket_read(&(mutant.server.socket), &header[0], sizeof(header[0]));
  socket_read(&(mutant.server.socket), &header[1], sizeof(header[1]));

  proc_header = header[0] & 0x0F;

  switch(proc_header)
  {
    case OPCODE_TEXT:   flags |= DATA_TEXT; break;
    case OPCODE_BINARY: flags |= DATA_BIN; break;
    default:            flags |= DATA_UNDEF; break;
  }

  length0 = (uint64_t)header[1];
  data_length = length0 & 0x000000000000007F;

  if (data_length == 126)
  {
    socket_read(&(mutant.server.socket), &header[0], sizeof(header[0]));
    socket_read(&(mutant.server.socket), &header[1], sizeof(header[1]));

    length0 = (((uint64_t)header[0]) << 8)  & 0x000000000000FF00;
    length1 = ((uint64_t)header[1])         & 0x00000000000000FF;
    data_length = length0 | length1;
  }
  else if (data_length == 127)
  {
    socket_read(&(mutant.server.socket), &header[0], sizeof(header[0]));
    socket_read(&(mutant.server.socket), &header[1], sizeof(header[1]));
    socket_read(&(mutant.server.socket), &header[2], sizeof(header[2]));
    socket_read(&(mutant.server.socket), &header[3], sizeof(header[3]));
    socket_read(&(mutant.server.socket), &header[4], sizeof(header[4]));
    socket_read(&(mutant.server.socket), &header[5], sizeof(header[5]));
    socket_read(&(mutant.server.socket), &header[6], sizeof(header[6]));
    socket_read(&(mutant.server.socket), &header[7], sizeof(header[7]));

    length0 = (((uint64_t)header[0]) << 56)   & 0xFF00000000000000;
    length1 = (((uint64_t)header[1]) << 48)   & 0x00FF000000000000;
    length2 = (((uint64_t)header[2]) << 40)   & 0x0000FF0000000000;
    length3 = (((uint64_t)header[3]) << 32)   & 0x000000FF00000000;
    length4 = (((uint64_t)header[4]) << 24)   & 0x00000000FF000000;
    length5 = (((uint64_t)header[5]) << 16)   & 0x0000000000FF0000;
    length6 = (((uint64_t)header[6]) << 8)    & 0x000000000000FF00;
    length7 = ((uint64_t)header[7])           & 0x00000000000000FF;

    data_length = length0 | length1 | length2 | length3 | length4 | length5 | length6 | length7;
  }
}

/**
 *  @brief  Procesa los datos de tipo texto.
 *
 *  Lee los datos de tipo de texto, que vienen en formato JSON. Después los descodifica
 *  para extraer los datos cuya clave es 'event', ya que indican el comando que ha mandado
 *  el servidor. Si el evento es 'ACK' enviamos el nombre y tipo del módulo.
 *
 *  @param  this  Puntero a una máquina de estados
 *  return  void
 */
static void text_proc(fsm_t* this)
{
  char* rcv_buf;
  char* event;
  char* data;
  char* msg;
  jsmn_parser json;
  jsmntok_t t[data_length];
  int pos, r;

  jsmn_init(&json);

  rcv_buf = (char*)malloc((data_length+1)*sizeof(char));
  *(rcv_buf + data_length) = '\0';
  for(pos = 0; pos < data_length; pos++)
  {
    socket_read(&(mutant.server.socket), (rcv_buf + pos), sizeof(*(rcv_buf+pos)));
  }

  r = jsmn_parse(&json, rcv_buf, strlen(rcv_buf), t, sizeof(t)/sizeof(t[0]));
  if (r < 0) {
    std_printf("Failed to parse JSON: %d\n", r);
  }

  if (jsoneq(rcv_buf, &t[1], "event") == 0)
  {
    event = (char*)malloc((t[2].end-t[2].start +1)*sizeof(char));
    for (pos = 0; pos < t[2].end-t[2].start; pos++)
    {
      *(event + pos) = *(rcv_buf + t[2].start + pos);
    }
    *(event + pos) = '\0';

    if (strcmp(event, "ACK") == 0)
    {
      data = (char*)malloc((t[4].end-t[4].start +1)*sizeof(char));
      for (pos = 0; pos < t[4].end-t[4].start; pos++)
      {
        *(data + pos) = *(rcv_buf + t[4].start + pos);
      }
      *(data + pos) = '\0';
      std_printf("%s\n", data);
      free(data);

      msg = "{\"event\": \"clientInfo\", \"name\": \"NODEMCU\", \"type\": \"R\"}";
      if (http_websocket_client_write(&mutant, OPCODE_TEXT, msg, 55) != 55)
      {
        std_printf("#ERROR: Cannot send websocket message\n");
      }
    }
    else
    {
      std_printf("Unexpected event: %s\n", event);
    }
    free(event);
  }
  free(rcv_buf);
}

/**
 *  @brief  Procesa los datos binarios.
 *
 *  Toma los datos binarios y los envía por SPI llamando a una función de
 *  mp3_decoder.h
 *
 *  @param  this  Puntero a una máquina de estados
 *  @return void
 */
static void bin_proc(fsm_t* this)
{
  uint8_t* rcv_buf;
  int pos;

  rcv_buf = (uint8_t*)malloc(data_length*sizeof(uint8_t));
  for(pos = 0; pos < data_length; pos++)
  {
    socket_read(&(mutant.server.socket), (rcv_buf + pos), sizeof(*(rcv_buf+pos)));
  }
  // std_printf(OSTR("DATOS BINARIOS\n"));
  sendMp3(rcv_buf, data_length);
  free(rcv_buf);
}
