/**
* @brief Cabecera - Comunicación con el módulo VS1003
*
* @file mp3_decoder.h
* @version 2.4
* @author David González Filoso <dgfiloso@b105.upm.es>
* @company B105 - Electronic Systems Lab
**/
#ifndef MP3_DECODER_H
#define MP3_DECODER_H

//  Configura el módulo VS1003 por SPI
void configureMp3(void);

//  Envía audio en MP3 al módulo VS1003 por SPI
void sendMp3(uint8_t* buf_p, size_t size);

#endif
