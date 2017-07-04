/**
* @brief Código - Lógica de control con el servidor Cerebro y gestión del audio recibido.
*
* Utilizando una máquina de estados de tipo Mealy gestiona la conexión con el servidor
* Cerebro a través de Websocket. Diferencia entre texto o datos binarios recibidos, para
* gestionarlo como un comando del sistema o como datos que tiene que enviar al descodificador.
*
* @file mutant.c
* @version 2.5
* @author David González Filoso <dgfiloso@b105.upm.es>
* @company B105 - Electronic Systems Lab
*/

#include "simba.h"
#include "jsmn.h"
#include "mutant.h"
#include "mp3_decoder.h"

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
  TCP,
  UDP,
  TEXT,
};

/*  Private functions prototypes --------------------------------*/
size_t rcv_socket_size(struct socket_t* s);

static int tcp_socket_data(fsm_t* this);
static int udp_socket_data(fsm_t* this);
static int undef_data(fsm_t* this);
static int text_data(fsm_t* this);
static int tcp_rcv(fsm_t* this);
static void tcp_header_proc(fsm_t* this);
static void text_proc(fsm_t* this);
static void udp_proc(fsm_t* this);

/*  Global variables ------------------------------------------*/
static struct http_websocket_client_t mutant;     //!<  Cliente de Websocket
static struct socket_t udp;                       //!<  Conexión UDP
static uint8_t flags;                             //!<  Flags para indicar el tipo de dato recibido
static uint64_t tcp_data_length;                  //!<  Longitud de los datos recibidos por TCP
static uint64_t udp_data_length;                  //!<  Longitud de los datos recibidos por UDP
static struct inet_addr_t udp_addr;               //!<  Dirección UDP de donde se reciben datos
static int udp_ready = 0;
static uint8_t* udp_buf;

//  Estados y transiciones de la máquina
static fsm_trans_t mutant_fsm[] = {
  { WAITING,  tcp_socket_data,  TCP,      tcp_header_proc },
  { WAITING,  udp_socket_data,  WAITING,  udp_proc },
  { TCP,      undef_data,       WAITING,  NULL            },
  { TCP,      text_data,        TEXT,     NULL            },
  { TEXT,     tcp_rcv,          WAITING,  text_proc       },
  {-1,        NULL,             -1,       NULL            }
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

  if(socket_module_init() != 0)
  {
    std_printf(OSTR("#ERROR: Socket Module Init Failed\n"));
    return -1;
  }

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

  if (socket_open_udp(&udp) != 0)
  {
    std_printf("#ERROR: UDP Init Failed");
    return (-1);
  }

  return (0);
}

/*  Private functions ------------------------------------------------------*/

/**
 *  @brief  Devuelve la cantidad de datos recibidos por el socket TCP.
 *
 *  Hace uso del objeto cliente de Websocket para devolver la cantidad de bytes
 *  almacenados en la memoria de entrada del socket TCP.
 *
 *  @param void
 *  @return size_t Tamaño de los datos recibidos
 */
size_t rcv_socket_size(struct socket_t* s)
{
  return s->input.u.recvfrom.left;
}

/**
 *  @brief  Función de cambio de estado, indica si se han recibido datos por el socket TCP.
 *
 *  Esta función devuelve 1 si el tamaño de los datos recibidos por el socket TCP es mayor de 0.
 *
 *  @param  this  Puntero a una máquina de estados
 *  @return int Entero que indica si se han recibido datos (1) o no (0)
 */
static int tcp_socket_data(fsm_t* this)
{
  if (rcv_socket_size(&(mutant.server.socket)) > 0) {
    return 1;
  } else {
    return 0;
  }
}

/**
 *  @brief  Función de cambio de estado, indica si se han recibido datos por el socket UDP.
 *
 *  Esta función devuelve 1 si el tamaño de los datos recibidos por el socket UDP es mayor de 0.
 *  Para ello es necesario usar la función socket_recvfrom(...) ya que con ella se reciben.
 *
 *  @param  this  Puntero a una máquina de estados
 *  @return int Entero que indica si se han recibido datos (1) o no (0)
 */
static int udp_socket_data(fsm_t* this)
{
  if (udp_ready == 1)
  {
    udp_buf = (uint8_t*)malloc(1024*sizeof(uint8_t));
    std_printf("Vamos a pedir datos por UDP\n");
    udp_data_length = socket_recvfrom(&udp, udp_buf, 1024, 0, &udp_addr);

    std_printf("udp_data_length %d\n", udp_data_length);
    if (udp_data_length > 0) {
      return 1;
    } else {
      free(udp_buf);
      return 0;
    }
  } else {
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
 *  @brief  Función de cambio de estado que indica si hay tantos
 *  datos TCP como dice el campo de longitud.
 *
 *  Esta función salta si la cantidad de datos es mayor o igual a la indicada
 *  por el campo de longitud. Si es menor los lee y los descarta.
 *
 *  @param  this  Puntero a una máquina de estados
 *  @return int Indica si se han recibido la cantidad de datos indicados (1)
 */
static int tcp_rcv(fsm_t* this)
{
  uint8_t* temp;
  int i, socket_size;

  socket_size = rcv_socket_size(&(mutant.server.socket));

  std_printf("%d %d\n", socket_size, tcp_data_length);
  if (socket_size >= tcp_data_length)
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
static void tcp_header_proc(fsm_t* this)
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
    default:            flags |= DATA_UNDEF; break;
  }

  length0 = (uint64_t)header[1];
  tcp_data_length = length0 & 0x000000000000007F;

  if (tcp_data_length == 126)
  {
    socket_read(&(mutant.server.socket), &header[0], sizeof(header[0]));
    socket_read(&(mutant.server.socket), &header[1], sizeof(header[1]));

    length0 = (((uint64_t)header[0]) << 8)  & 0x000000000000FF00;
    length1 = ((uint64_t)header[1])         & 0x00000000000000FF;
    tcp_data_length = length0 | length1;
  }
  else if (tcp_data_length == 127)
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

    tcp_data_length = length0 | length1 | length2 | length3 | length4 | length5 | length6 | length7;
  }
}

/**
 *  @brief  Procesa los datos de tipo texto.
 *
 *  Lee los datos de tipo de texto, que vienen en formato JSON. Después los descodifica
 *  para extraer los datos cuya clave es 'event', ya que indican el comando que ha mandado
 *  el servidor. Si el evento es 'ACK' enviamos el nombre y tipo del módulo. Su el evento
 *  es 'udpRx' lee los datos, ya que contiene la IP de la que tiene que recibir datos, y
 *  se conecta a la IP que indican.
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
  jsmntok_t t[tcp_data_length];
  int pos, r;

  jsmn_init(&json);

  rcv_buf = (char*)malloc((tcp_data_length+1)*sizeof(char));
  *(rcv_buf + tcp_data_length) = '\0';
  for(pos = 0; pos < tcp_data_length; pos++)
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
    else if (strcmp(event, "udpRx") == 0)
    {
      data = (char*)malloc((t[4].end-t[4].start +1)*sizeof(char));
      for (pos = 0; pos < t[4].end-t[4].start; pos++)
      {
        *(data + pos) = *(rcv_buf + t[4].start + pos);
      }
      *(data + pos) = '\0';

      inet_aton(data, &(udp_addr.ip));
      udp_addr.port = 3000;
      if (socket_connect(&udp, &udp_addr) != 0)
      {
        std_printf("#ERROR: Cannot connect UDP socket\n");
      }
      if (socket_bind(&udp, &udp_addr) != 0)
      {
        std_printf("#ERROR: Cannot bind UDP socket\n");
      }

      udp_ready = 1;
      std_printf("UDP_RX on %s\n", data);
      free(data);
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
 *  @brief  Procesa los datos binarios que provienen de la conexión UDP.
 *
 *  Toma los datos binarios y los envía por SPI llamando a una función de
 *  mp3_decoder.h
 *
 *  @param  this  Puntero a una máquina de estados
 *  @return void
 */
static void udp_proc(fsm_t* this)
{
  //  Tenemos que enviar desde el byte 12,
  //  ya que los primeros 12 bytes son cabecera

  std_printf("DATOS MULTIMEDIA\n");
  // sendMp3(udp_buf, udp_data_length);
  free(udp_buf);
}
