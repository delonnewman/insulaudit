#!/usr/bin/python
import user

import struct
import sys
import serial
import time
import logging
from pprint import pprint, pformat

from insulaudit.core import Command
from insulaudit.clmm.usbstick import *
from insulaudit import lib

logging.basicConfig( stream=sys.stdout )
log = logging.getLogger( 'auditor' )
log.setLevel( logging.DEBUG )
log.info( 'hello world' )
io  = logging.getLogger( 'auditor.io' )
io.setLevel( logging.DEBUG )

"""
This analysis from 2011-07 looks similar to ComLink1 It doesn't seem to work
with my White CareLinkUSB Device.  Also, the log of previous runs contains 0x04
commands (ProductInfo) only found in ComLink2.
#####################
#
# Command Stuff
# (pseudocode analysis of MM512.java)
 The Pump Packet looks like this:
 7 bytes with parameters on the end
 00     167
 01     serial[ 0 ]
 02     serial[ 1 ]
 03     serial[ 2 ]
 04     commandCode
 05     sequenceNumber or paramCount
 06     [ parameters ]
 06/07  CRC8(packet)

 or:
 167, serial, code, seq/param, params, CRC8(packet)
NB the whole thing is wrapped by encodeDC()

get ACK packet: is:
packet = [ 167 ] + serial + [ 6, 0 ]
packet.append(CRC8(packet))

buildPacket:
  # 7 bytes + params
  packet = [ ]
  head   = [ 167, ] + serial 
  body   = [ self.code ]
  tail   = [ 0 ]
  if paramCount > 0:
    if sequenceNumber:
      tail = [ sequenceNumber ]
    else:
      tail = [ paramCount ]
    tail.append( commandParams )
  packet = head + body + tail
  packet.append(CRC8(packet))
  return encodeDC(packet)

makeCommandPacket:
  # returns a new "Command"
  # which special cases 93
  command = Command(self.code, 0, 0, 0)
  if code == 93 and commandParams[0] == 1:
    # 
    command.setUseMultiXmitMode(true)
  return command

makeDataPacket(packetNumber, sequenceNumber, paramCount):
  command = Command(self.code, 0, 0, self.commandType)
  command.paramCount     = paramCount
  command.sequenceNumber = sequenceNumber
  command.params         = self.params[packetOffset:packetOffset+packetSize]
  return command


"""

"""
#####################
#
# Pump Stuff
# (pseudocode analysis of MM512.java)
sendAck:
  packet = [ 167 ] + serial + [ 6, 0 ]
  packet.append(CRC8(packet))
  packet = encodeDC(packet)

  com_command = [ 5, packet.length ]
  serial.write(com_command + packet)
  usb.readAckByte()
  # turn off RF
  usb.readReadyByte(false)

checkAck:
  bytesAvail = usb.readStatus( )
  usb.sendTransferDataCommand( ) # exec read data flow on usb
  response = serial.read( )
  ack = decodeDC(response)
  # can check header and CRC of response
  # should match the previously sent command
  ackBytes[4] == 6 # command ACK ok
  error = lookup_error(ackBytes[5])

initDevice:
  cmdPowerControl.execute()
  readPumpModelNumber.execute()
  cmdReadError.execute()
  cmdReadState.execute()
  cmdReadTmpBasal.execute()
  
initDeviceAfterModelNumberKnown()
  bolus = detectActiveBolus()
  if !bolus:
    cmdSetSuspend.execute()

detectActiveBolus:
  cmdDetectBolus.execute()
  # make sure it worked

shutdownPump
  cmdCancelSuspend.execute()

execute:
  # retry 3 times
  # if not ready, do usb.initCommunications
  executeIO()

executeIO:
  if paramCount > 0:
    packet = makeCommandPacket()
    packet.executeIO()
  
  if paramCount > 128:
    data = makeDataPacket(1, 1, 64)
    data.sendAndRead()

    data = makeDataPacket(2, 2, 64)
    data.sendAndRead()

    data = makeDataPacket(3, 131, 16)
    data.sendAndRead()
  elsif paramCount > 64:
    data = makeDataPacket(1, 1, 64)
    data.sendAndRead()

    data = makeDataPacket(2, 130, 32)
    data.sendAndRead()
  else:
    # special case commandCode == 64
    sendAndRead()

sendAndRead:
  sendCommand()
  if expectedLength > 0 and !isHaltRequested():
    if pages
      data = readDeviceDataPage(length)
    else:
      data = readDeviceData()
      bytesRead += data.length
  else
    if commandParams.length > 0:
      # setState(7)
      bytesRead += commandParams.length
      
      checkAck()

sendCommand
  packet = buildPacket()
  usbCmd = 0
  # only when cmd ==93 (powerCTRL)
  if isUseMultiXmitMode():
    usbCmd = 10
  elsif paramCount == 0:
    usbCmd = 5
  else:
    # turn on RFMode, new session
    usbCmd = 4
  usbCmd = [ usbCmd, packet.length ]
  command = usbCmd + packet
  serial.write(command)
  usb.readAckByte()
  # special case command 93 and paramCount == 0
  # needs to be sensitive to timeout
  usb.readReadyByte(usbCmd[0] == 4)

checkHeaderAndCRC(deviceData):
  # check CRC8
  # check serial number


readDeviceDataPage(expectedBytes):
  # collect multiple pages of data for commands with longer reads.
  done = False
  pages = [ ]
  while not done:
    # get a page
    data = readDeviceData()
    # if no more data we're done
    if data.length == 0
      done = true
    else
      # add data to pages
      pages.append(data)
      done = pages.length >= expectedBytes || isHaltRequested()
      # sendAck to acknowledge receipt of this page
      if not done and isHaltRequested():
        sendAck()
  return pages

readDeviceData:
  bytesAvail = usb.readStatus( )
  usb.sendTransferDataCommand( ) # exec read data flow on usb
  response = decodeDC(serial.read( ))
  ack = usb.readAckByte()
  if (!ack) throw IOException
  checkHeaderCRC(response)
  response[5] is NAK (21) # look up NAK
  if response[4] != commandCode # throw Error
  dataLen = response[5] # length
  cpyLen = len(response) - 6 - 1
  return response[6:-1]


packSerial
  return makePackedBCD(serial)

set/isUseMultiXmitMode: # simple getter/setter for m_useMultiXmitMode

Command(code, bytesPerRecord, maxRecords, address, addressLength, commandType)
XXX: acquireDataFromDevice, acquireDataFromDeviceConclusion only have disassembly, making it a bit harder to understand.

"""

"""

##########
#
# USB Device
#


"""
from insulaudit import core, lib
from insulaudit.clmm import usbstick
from pprint import pprint, pformat

class Link( core.CommBuffer ):
  class ID:
    VENDOR  = 0x0a21
    PRODUCT = 0x8001
  timeout = .100
  def __init__( self, port, timeout=None ):
    super(type(self), self).__init__(port, timeout)

  def initUSBComms(self):
    log.info('initUSBComms')
    log.info('readUntilEmpty')
    # clear the buffer
    self.readUntilEmpty( )
    # set RS232 MODE On
    # check success, first byte == 51 READY
    log.info(pformat(self.process( usbstick.USBProductInfo( ) ).info ))
    log.info('prep for rf comms, turn on RS232 MODE')
    #assert self.sendCommandCheckReply(6, 51)
    assert self.sendCommandCheckReply(6, 51)
    log.info("read status")
    numOldBytes = self.readStatus( )
    if numOldBytes > 0:
      self.serial.setTimeout(10)
      self.sendTransferDataCommand( )
      message = self.read( )
      assert self.readAckByte()
  
  def readAckByte(self):
    # retries twice
    return self.read(1) == 'U' # 85
    # else NAK == 'f' # 102

  def readUntilEmpty(self):
    lines = True
    while lines:
      lines = self.readlines( )
      log.debug('emptying buffer: %s' % lines)

  def readStatus(self):
    # sets m_status, used to decode receivedByteCount, hasData, RS232Mode,
    # FilterRepeat, AutoSleep, Status Error, SelfTestError
    log.info('read Status')
    self.status = self.sendCommandGetReply(2)
    time.sleep(2)
    bytesAvailable = self.read(1)
    log.info('bytesAvailable: %r' % bytesAvailable)
    # TODO
    assert self.readAckByte() # serial.read(1) == ACK
    return bytesAvailable

  def sendCommandGetReply(self, command):
    self.sendCommand(command)
    delay = 2
    time.sleep(delay)
    return bytearray(self.read(1))

  def sendCommandCheckReply(self, command, expect):
    # retries twice
    reply = None
    ok    = False
    for i in xrange(2):
      reply = self.sendCommandGetReply(command)
      log.info('sendCommandGetReply:attempt:expect:%r:%s:reply:%s' % (expect, i, reply))
      if reply == expect: break
    return reply == expect

  def sendCommand(self, command):
    self.write(str(bytearray([command, 0])))

  def sendDataTransferCommand(self):
    # data transfer command
    self.sendCommand(8)

  def setRfMode(self):
    self.sendCommand(7)
    # sleep
    time.sleep(2)
    self.readAckByte()

  def readReadyByte(self, setRFMode):
    #retries twice
    self.readReadyByteIO(setRFMode)
    # adjust sleep timing

  def readReadyByteIO(self, setRFMode=False):
    # for some reason this is tightly coupled
    if setRfMode:
      self.setRfMode()
    # retries twice
    return self.read(1) == 51

  def process( self, command ):
    x = str( command )
    self.serial.setTimeout( command.timeout )
    log.debug( 'setting timeout: %s' % command.timeout )
    io.info( 'carelink.command: %r\n%s' % ( command,
                                            command.hexdump( ) ) )
    self.write( x )
    #self.write( x )
    log.debug( 'sent command, waiting' )
    time.sleep( command.sleep )
    reply = command( self )
    return reply

class Command(object):
  def __init__(self):
    pass
  def format(self):
    pass
  def execute(self, link):
    pass

if __name__ == '__main__':
  io.info("hello world")

  port = None
  try:
    port = sys.argv[1]
  except IndexError, e:
    print "usage:\n%s /dev/ttyUSB0" % sys.argv[0]
    sys.exit(1)
    
  link = Link(port)
  link.initUSBComms()
  #pprint( carelink( USBProductInfo(      ) ).info )


#####
# EOF
