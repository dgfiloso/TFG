/**
* @brief Cabecera - Conexión con una red WiFi.
*
* @file wifi_conn.h
* @version 2.5
* @author David González Filoso <dgfiloso@b105.upm.es>
* @company B105 - Electronic Systems Lab
**/

#ifndef WIFI_CONN_H
#define WIFI_CONN_H

//  Conexión a red wifi
int wifi_connect(const char* ssid_p, const char* passw_p);

#endif
