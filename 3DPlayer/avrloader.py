#!/usr/bin/env python

"""
    Logging utility with a syslog like API. It is set up to log to
    the command line to provide program progress and error messages.
"""

import logging
import os.path
import sys

LOG_PID = None
LOG_DAEMON = None

LOG_CRIT = logging.CRITICAL
LOG_ERR = logging.ERROR
LOG_WARNING = logging.WARNING
LOG_INFO = logging.INFO
LOG_DEBUG = logging.DEBUG

gident = os.path.basename(sys.argv[0])
gpriority = LOG_DEBUG
gsilent = False
gprogress = True


def openlog(ident=None, logopt=None, facility=None):
    global gident
    if ident != None:
        gident = ident

    logging.basicConfig(
        stream=sys.stdout,
        format="%(asctime)s: ["
        + gident
        + "]: %(module)s:%(lineno)d %(levelname)s: %(message)s",
        level=logging.DEBUG,
    )


def avrlog(priority=None, message=None, use_fmt=True):
    """
    Output a syslog like message.
    """
    global gsilent
    global gpriority
    if gsilent:
        return

    if priority != None:
        gpriority = priority
    if use_fmt:
        if gpriority == LOG_CRIT:
            logging.critical(message)
        elif gpriority == LOG_ERR:
            logging.error(message)
        elif gpriority == LOG_WARNING:
            logging.warning(message)
        elif gpriority == LOG_INFO:
            logging.info(message)
        else:
            logging.debug(message)
    elif gpriority >= logging.root.level:
        sys.stdout.write(message)


def progress(message=None):
    """
    Output a progress message.
    """
    global gprogress
    if gprogress and message != None:
        sys.stdout.write(message)
        sys.stdout.flush()


def set_silent(silent=True):
    """
    Enable or disable avrlog messages.
    """
    global gsilent
    gsilent = silent


def set_progress(progress=True):
    """
    Enable or disable progress messages.
    """
    global gprogress
    gprogress = progress


def setlogmask(level):
    logging.root.setLevel(level)


def LOG_UPTO(level):
    return level


def closelog():
    logging.shutdown()


"""
    The classes to interface with the user and invoke commands.
"""
import os  # @Reimport
import getopt
import sys  # @Reimport
import serial
import time


class JobInfo:
    """
    JobInfo class.
    This class deals with the command line input from the user. The
    command line is parsed. If a valid command is detected then a job
    is run. If an invalid command is detected then the usage message
    is displayed and the user is returned to the command line.
    """

    def __init__(self):

        self.show_help = False
        self.silent_mode = False
        self.no_progress_indicator = False
        self.read_signature = False
        self.chip_erase = False
        self.get_hw_revision = False
        self.get_sw_revision = False
        self.program_flash = False
        self.program_eeprom = False
        self.read_flash = False
        self.read_eeprom = False
        self.verify_flash = False
        self.verify_eeprom = False
        self.read_lock_bits = False
        self.read_fuse_bits = False
        self.read_osccal = False
        self.rc_calibrate = False

        self.device_name = ""
        self.input_file_flash = ""
        self.input_file_eeprom = ""
        self.output_file_flash = ""
        self.output_file_eeprom = ""

        self.osccal_parameter = -1
        self.osccal_flash_address = -1
        self.osccal_flash_address_tiny = -1
        self.calib_retval = -1
        self.osccal_eeprom_address = -1

        self.program_lock_bits = -1
        self.verify_lock_bits = -1

        self.program_fuse_bits = -1
        self.program_extended_fuse_bits = -1
        self.verify_fuse_bits = -1
        self.verify_extended_fuse_bits = -1

        self.memory_fill_pattern = -1

        self.flash_start_address = -1
        self.flash_end_address = -1

        self.eeprom_start_address = -1
        self.eeprom_end_address = -1

        self.com_port_name = ""
        self.baud = 9600
        self.timeout = 2.0
        self.search_path = ""

        self.encrypted = False

    def parse_command_line(self, argv):

        own_path = argv[0]
        slash_pos = argv[0].rfind(os.sep)
        if slash_pos == -1:
            own_path = "."
        else:
            own_path = argv[0][:slash_pos]

        self.search_path = own_path
        self.search_path = "%s%s%s%sdevices" % (
            self.search_path,
            os.pathsep,
            own_path,
            os.sep,
        )

        try:
            optlist, args = getopt.getopt(  # @UnusedVariable
                argv[1:],
                "b:c:ed:E:f:F:gG:h?l:L:nO:qsx:yY:z",
                [
                    "af=",
                    "ae=",
                    "if=",
                    "ie=",
                    "of=",
                    "oe=",
                    "O#=",
                    "pf",
                    "pe",
                    "pb",
                    "rf",
                    "re",
                    "rb",
                    "Sf=",
                    "Se=",
                    "vf",
                    "ve",
                    "vb",
                ],
            )
            for x, y in optlist:
                if x == "--af":
                    self.flash_start_address, self.flash_end_address = y.split(":")
                    self.flash_start_address = int(self.flash_start_address, 16)
                    self.flash_end_address = int(self.flash_end_address, 16)
                elif x == "--ae":
                    self.eeprom_start_address, self.eeprom_end_address = y.split(":")
                    self.eeprom_start_address = int(self.eeprom_start_address, 16)
                    self.eeprom_end_address = int(self.eeprom_end_address, 16)
                elif x == "-b":
                    if y == "h":
                        self.get_hw_revision = True
                    elif y == "s":
                        self.get_sw_revision = True
                    else:
                        raise RuntimeError("Invalid programmer revision request.")
                elif x == "-c":
                    self.com_port_name = y
                elif x == "-d":
                    self.device_name = y
                elif x == "-e":
                    self.chip_erase = True
                elif x == "-E":
                    self.program_extended_fuse_bits = int(y, 16)
                elif x == "-f":
                    self.program_fuse_bits = int(y, 16)
                elif x == "-F":
                    self.verify_fuse_bits = int(y, 16)
                elif x == "-g":
                    self.silent_mode = True
                elif x == "-G":
                    self.verify_extended_fuse_bits = int(y, 16)
                elif x == "-h" or x == "-?":
                    self.show_help = True
                elif x == "--if":
                    self.input_file_flash = y
                elif x == "--ie":
                    self.input_file_eeprom = y
                elif x == "-l":
                    self.program_lock_bits = int(y, 16)
                elif x == "-L":
                    self.verify_lock_bits = int(y, 16)
                elif x == "-n":
                    self.encrypted = True
                elif x == "--of":
                    self.output_file_flash = y
                elif x == "--oe":
                    self.output_file_eeprom = y
                elif x == "-O":
                    self.read_osccal = True
                    self.osccal_parameter = int(y, 16)
                elif x == "--O#":
                    self.read_osccal = False
                    self.osccal_parameter = int(y, 16)
                elif x == "--pf":
                    self.program_flash = True
                elif x == "--pe":
                    self.program_eeprom = True
                elif x == "--pb":
                    self.program_flash = True
                    self.program_eeprom = True
                elif x == "-q":
                    self.read_fuse_bits = True
                elif x == "--rf":
                    self.read_flash = True
                elif x == "--re":
                    self.read_eeprom = True
                elif x == "--rb":
                    self.read_flash = True
                    self.read_eeprom = True
                elif x == "-s":
                    self.read_signature = True
                elif x == "--Sf":
                    self.osccal_flash_address = int(y, 16)
                elif x == "--Se":
                    self.osccal_eeprom_address = int(y, 16)
                elif x == "--vf":
                    self.verify_flash = True
                elif x == "--ve":
                    self.verify_eeprom = True
                elif x == "--vb":
                    self.verify_flash = True
                    self.verify_eeprom = True
                elif x == "-x":
                    self.memory_fill_pattern = int(y, 16)
                elif x == "-y":
                    self.read_lock_bits = True
                elif x == "-Y":
                    self.rc_calibrate = True
                    self.osccal_flash_address_tiny = int(y, 16)
                elif x == "-z":
                    self.no_progress_indicator = True
                else:
                    self.usage()
                    sys.exit(1)
        except:
            self.usage()
            sys.exit(1)

    def set_comms(self, device, baud, timeout):

        self.com_port_name = device
        self.baud = baud
        self.timeout = timeout

    def do_job(self):

        if self.silent_mode:
            set_silent()
            set_progress(False)

        if self.no_progress_indicator:
            set_progress(False)

        if self.show_help:
            self.usage()
            return

        port = None
        prog = None
        if len(self.com_port_name) > 0:
            """
            # This forces a reset to get into bootloader
            port = serial.Serial(port=self.com_port_name, baudrate=1200)
            port.close()
            time.sleep(1)
            # Re-connect after reset completes while still in bootloader
            """
            port = serial.Serial(
                port=self.com_port_name,
                baudrate=self.baud,
                timeout=self.timeout,
                writeTimeout=self.timeout,
            )
            prog = AVRProgrammer.instance(port)
        else:
            avrlog(LOG_ERR, "Serial port not specified.")

        if prog == None:
            raise RuntimeError("AVR Programmer not found.")

        if self.rc_calibrate:
            if not prog.rc_calibrate():
                avrlog(LOG_ERR, "RC calibrate failed.")
                sys.exit(1)
            else:
                avrlog(LOG_INFO, "RC calibrate succeeded.")

        avrlog(LOG_INFO, "Entering programming mode...")
        if not prog.enter_programming_mode():
            avrlog(LOG_ERR, "Set programming mode failed.")
            sys.exit(1)
        else:
            avrlog(LOG_INFO, "Set programming mode succeeded.")

        if self.read_signature:
            avrlog(LOG_CRIT, "Reading signature bytes: ", False)
            sig0, sig1, sig2 = prog.read_signature()
            avrlog(LOG_CRIT, "0x%02x, 0x%02x, 0x%02x\n" % (sig0, sig1, sig2), False)

        if self.get_sw_revision:
            avrlog(LOG_CRIT, "Reading programmer software revision: ", False)
            res, major, minor = prog.programmer_software_version()
            if res:
                avrlog(LOG_CRIT, "%s.%s\n" % (major, minor), False)
            else:
                avrlog(LOG_CRIT, "\nError retrieving software revision.\n", False)

        if len(self.device_name) == 0:
            avrlog(LOG_ERR, "Device name not specified.")
            return

        device = AVRDevice(self.device_name)
        device.read_avr_parameters(self.search_path)

        sig0, sig1, sig2 = device.get_signature()
        if not prog.check_signature(sig0, sig1, sig2):
            avrlog(LOG_ERR, "Signature does not match device.")

        self._do_device_dependent(prog, device)

        prog.leave_programming_mode()

        if port != None:
            port.close()

    def _do_device_dependent(self, prog, device):

        prog.set_page_size(device.get_page_size())

        if self.flash_end_address != -1:
            if self.flash_end_address >= device.get_flash_size():
                raise RuntimeError(
                    "Specified flash address is outside of "
                    + "the device address space"
                )
        else:
            self.flash_start_address = 0
            self.flash_end_address = device.get_flash_size() - 1

        if self.eeprom_end_address != -1:
            if self.eeprom_end_address >= device.get_eeprom_size():
                raise RuntimeError(
                    "Specified EEPROM address is outside of "
                    + "the device address space"
                )
        else:
            self.eeprom_start_address = 0
            self.eeprom_end_address = device.get_eeprom_size() - 1

        if self.read_flash:

            if len(self.output_file_flash) == 0:
                raise RuntimeError("Cannot read flash without output file specified.")

            hexf = HexFile(device.get_flash_size())
            hexf.set_used_range(self.flash_start_address, self.flash_end_address)

            avrlog(LOG_INFO, "Reading flash contents...")

            if not prog.read_flash(hexf):
                raise RuntimeError("Flash read is not supported by this programmer.")

            avrlog(LOG_INFO, "Writing Hex output file...")
            hexf.write_file(self.output_file_flash)

        if self.read_eeprom:

            if len(self.output_file_eeprom) == 0:
                raise RuntimeError("Cannot read EEPROM without file specified.")

            hexf = HexFile(device.get_eeprom_size())
            hexf.set_used_range(self.eeprom_start_address, self.eeprom_end_address)

            avrlog(LOG_INFO, "Reading EEPROM contents...")

            if not prog.read_eeprom(hexf):
                raise RuntimeError("EEPROM read is not supported by the programmer.")

            avrlog(LOG_INFO, "Writing Hex output file...")
            hexf.write_file(self.output_file_eeprom)

        if self.read_lock_bits:

            avrlog(LOG_INFO, "Reading lock bits...")
            result, bits = prog.read_lock_bits()
            if not result:
                raise RuntimeError("Lock bit read is not supported by the programmer.")

            avrlog(LOG_ERR, "Lock bits: 0x%02X\n" % bits, False)

        if self.read_fuse_bits:

            if not device.get_fuse_status():
                raise RuntimeError("Selected device has no fuse bits.")

            avrlog(LOG_INFO, "Reading fuse bits...")

            result, bits = prog.read_fuse_bits()
            if not result:
                raise RuntimeError("Fuse bit read is not supported by the programmer.")

            avrlog(LOG_ERR, "Fuse bits: 0x%04X\n" % bits, False)

            if device.get_ext_fuse_status():

                result, bits = prog.read_extended_fuse_bits()
                if not result:
                    raise RuntimeError(
                        "Extended fuse bit read is not supported by this programmer."
                    )

                avrlog(LOG_ERR, "Extended fuse bits: %0x02X" % bits, False)

        if self.chip_erase:

            avrlog(LOG_INFO, "Erasing chip contents...")

            if not prog.chip_erase():
                raise RuntimeError("Chip erase is not supported by this programmer.")

        if self.program_flash or self.verify_flash:

            if len(self.input_file_flash) == 0:
                raise RuntimeError(
                    "Cannot program or verify flash without a file specified."
                )

            hexf = HexFile(device.get_flash_size())

            if self.memory_fill_pattern != -1:
                hexf.clear_all(self.memory_fill_pattern)

            avrlog(LOG_INFO, "Reading hex input file for flash operation...")

            hexf.read_file(self.input_file_flash)

            if (
                hexf.get_range_start() > self.flash_end_address
                or hexf.get_range_end() < self.flash_start_address
            ):
                raise RuntimeError("Hex file defines data outside specified range.")

            # Added this as it was the only way to get it to honor the flash_start_address and flash_end_address, otherwise it would defer to the hexfiles address range which would erase the bootloader
            if (
                hexf.get_range_start() < self.flash_start_address
                or hexf.get_range_end() > self.flash_end_address
            ):
                avrlog(
                    LOG_INFO,
                    f"Updating HexFile used range to {self.flash_start_address} through {self.flash_end_address}...",
                )
                hexf.set_used_range(self.flash_start_address, self.flash_end_address)

            if self.memory_fill_pattern == -1:

                if hexf.get_range_start() > self.flash_start_address:
                    self.flash_start_address = hexf.get_range_start()

                if hexf.get_range_end() < self.flash_end_address:
                    self.flash_end_address = hexf.get_range_end()

            if self.rc_calibrate:

                if (
                    self.osccal_flash_address_tiny > self.flash_start_address
                    and self.osccal_flash_address_tiny < self.flash_end_address
                ):
                    raise RuntimeError("Specified address is within application code.")

                hexf.set_data(self.osccal_flash_address_tiny, self.calib_retval)
                hexf.set_used_range(
                    self.flash_start_address, self.osccal_flash_address_tiny
                )

        if self.program_flash:

            avrlog(LOG_INFO, "Programming flash contents...")
            if not prog.write_flash(hexf):
                raise RuntimeError(
                    "Flash programming is not supported by this programmer."
                )

        if self.verify_flash:

            hexv = HexFile(device.get_flash_size())

            avrlog(LOG_INFO, "Reading flash contents...")

            hexv.set_used_range(hexf.get_range_start(), hexf.get_range_end())

            if not prog.read_flash(hexv):
                raise RuntimeError("Flash read is not supported by this programmer.")

            avrlog(LOG_INFO, "Comparing flash data...")

            for pos in range(hexf.get_range_start(), hexf.get_range_end() + 1):

                valf = hexf.get_data(pos)
                valv = hexv.get_data(pos)
                if valf != valv:
                    avrlog(
                        LOG_ERR,
                        "Unverified at 0x%X (0x%02X vs 0x%02X)\n" % (pos, valf, valv),
                        False,
                    )
                    break

            if pos >= hexf.get_range_end():
                avrlog(LOG_ERR, "Verified.\n", False)

        if self.program_eeprom or self.verify_eeprom:

            if len(self.input_file_eeprom) == 0:
                raise RuntimeError(
                    "Cannot program or verify EEPROM without a file specified."
                )

            hexf = HexFile(device.get_eeprom_size())

            if self.memory_fill_pattern != -1:
                hexf.clear_all(self.memory_fill_pattern)

            avrlog(LOG_INFO, "Reading hex file for EEPROM operations...")

            hexf.read_file(self.input_file_eeprom)

            if (
                hexf.get_range_start() > self.eeprom_end_address
                or hexf.get_range_end() < self.eeprom_start_address
            ):
                raise RuntimeError("Hex file defines data outside of specified range.")

            if self.memory_fill_pattern == -1:
                if hexf.get_range_start() > self.eeprom_start_address:
                    self.eeprom_start_address = hexf.get_range_start()

                if hexf.get_range_end() < self.eeprom_end_address:
                    self.eeprom_end_address = hexf.get_range_end()

            hexf.set_used_range(self.eeprom_start_address, self.eeprom_end_address)

        if self.program_eeprom:

            avrlog(LOG_INFO, "Programming EEPROM contents...")
            if not prog.write_eeprom(hexf):
                raise RuntimeError(
                    "EEPROM programming is not supported by this programmer."
                )

        if self.verify_eeprom:

            hexv = HexFile(device.get_eeprom_size())

            avrlog(LOG_INFO, "Reading EEPROM contents...")

            hexv.set_used_range(hexf.get_range_start(), hexf.get_range_end())

            if not prog.read_eeprom(hexv):
                raise RuntimeError("EEPROM read is not supported by this programmer.")

            avrlog(LOG_INFO, "Comparing EEPROM data...")

            for pos in range(hexf.get_range_start(), hexf.get_range_end() + 1):

                valf = hexf.get_data(pos)
                valv = hexv.get_data(pos)
                if valf != valv:
                    avrlog(
                        LOG_ERR,
                        "Unverified at address 0x%X (0x%02X vs 0x%02X)\n"
                        % (valf, valv),
                        False,
                    )
                    break

            if pos >= hexf.get_range_end():
                avrlog(LOG_ERR, "Verified.\n", False)

        if self.program_lock_bits != -1:

            avrlog(LOG_INFO, "Programming lock bits...")

            if not prog.write_lock_bits(self.program_lock_bits):
                raise RuntimeError(
                    "Lock bit programming is not supported by this programmer."
                )

        if self.program_fuse_bits != -1:

            if not device.get_fuse_status():
                raise RuntimeError("Selected device has no fuse bits.")

            avrlog(LOG_INFO, "Programming fuse bits...")

            if not prog.write_fuse_bits(self.program_fuse_bits):
                raise RuntimeError(
                    "Fuse bit programming is not supported by this programmer."
                )

        if self.program_extended_fuse_bits != -1:

            if not device.get_extended_fuse_status():
                raise RuntimeError("Selected device has no extended fuse bits.")

            avrlog(LOG_INFO, "Programming extended fuse bits...")

            if not prog.write_extended_fuse_bits(self.program_extended_fuse_bits):
                raise RuntimeError(
                    "Extended fuse bit programming is not supported by this programmer."
                )

        if self.verify_lock_bits != -1:

            avrlog(LOG_INFO, "Verifying lock bits...")

            result, bits = prog.read_lock_bits()
            if not result:
                raise RuntimeError("Lock bit read is not supported by this programmer.")

            if bits == self.verify_lock_bits:
                avrlog(LOG_ERR, "Lock bits verified.\n", False)
            else:
                avrlog(
                    LOG_ERR,
                    "Lock bits differ (0x%02X vs 0x%02X)\n"
                    % (self.verify_lock_bits, bits),
                    False,
                )

        if self.verify_fuse_bits != -1:

            if not device.get_fuse_status():
                raise RuntimeError("Selected device has no fuse bits.")

            avrlog(LOG_INFO, "Verifying fuse bits...")

            result, bits = prog.read_fuse_bits()
            if not result:
                raise RuntimeError("Fuse bit read is not supported by this programmer.")

            if bits == self.verify_fuse_bits:
                avrlog(LOG_ERR, "Fuse bits (0x%04X) verified.\n" % bits, False)
            else:
                avrlog(
                    LOG_ERR,
                    "Fuse bits differ (0x%04X vs 0x%04X)\n"
                    % (self.verify_fuse_bits, bits),
                    False,
                )

        if self.verify_extended_fuse_bits != -1:

            if not device.get_ext_fuse_status():
                raise RuntimeError("Selected device has no extended fuse bits.")

            avrlog(LOG_INFO, "Verifying extended fuse bits...")

            result, bits = prog.read_extended_fuse_bits()
            if not result:
                raise RuntimeError(
                    "Extended fuse bit read is not supported by this programmer."
                )

            if bits == self.verify_extended_fuse_bits:
                avrlog(LOG_ERR, "Extended fuse bits verified.\n", False)
            else:
                avrlog(
                    LOG_ERR,
                    "Extended fuse bits differ (0x%02X vs 0x%02X).\n"
                    % (self.verify_fuse_bits, bits),
                    False,
                )

        if self.osccal_parameter != -1:

            if self.read_osccal:

                avrlog(LOG_INFO, "Reading OSCCAL from device...")

                pos = self.osccal_parameter
                result, self.osccal_parameter = prog.read_osccal(pos)
                if not result:
                    raise RuntimeError(
                        "OSCCAL read is not supported by this programmer."
                    )

                avrlog(
                    LOG_ERR, "OSCCAL parameter: 0x%02X" % self.osccal_parameter, False
                )

        if self.osccal_flash_address != -1:

            if self.osccal_parameter == -1:
                raise RuntimeError("OSCCAL value not specified.")

            avrlog(LOG_INFO, "Programming OSCCAL to flash...")

            if not prog.write_flash_byte(
                self.osccal_flash_address, self.osccal_parameter
            ):
                raise RuntimeError(
                    "Flash programming is not supprted by this programmer."
                )

        if self.osccal_eeprom_address != -1:

            if self.osccal_parameter == -1:
                raise RuntimeError("OSCCAL value not specified.")

            avrlog(LOG_INFO, "Programming OSCCAL to EEPROM...")

            if not prog.write_eeprom_byte(
                self.osccal_eeprom_address, self.osccal_parameter
            ):
                raise RuntimeError(
                    "EEPROM programming is not supported by this programmer."
                )

    def usage(self):

        print("Command Line Switches:")
        print("        [-d device name] [--if infile] [--ie infile] [--of outfile]")
        print(
            "        [--oe outfile] [-s] [-O index] [--O# value] [--Sf addr] [--Se addr]"
        )
        print(
            "        [-e] [--p[f|e|b]] [--r[f|e|b]] [--v[f|e|b]] [-l value] [-L value]"
        )
        print(
            "        [-y] [-f value] [-E value] [-F value] [-G value] [-q] [-x value]"
        )
        print(
            "        [--af start:stop] [--ae start:stop] [-c port] [-b h|s] [-g] [-z]"
        )
        print("        [-Y] [-n] [-h|?]")
        print("")
        print("Parameters:")
        print("-d      Device name. Must be applied when programming the device.")
        print(
            "--if    Name of FLASH input file. Required for programming or verification"
        )
        print("        of the FLASH memory. The file format is Intel Extended HEX.")
        print(
            "--ie    Name of EEPROM input file. Required for programming or verification"
        )
        print("        of the EEPROM memory. The file format is Intel Extended HEX.")
        print(
            "--of    Name of FLASH output file. Required for readout of the FLASH memory."
        )
        print("        The file format is Intel Extended HEX.")
        print("--oe    Name of EEPROM output file. Required for readout of the EEPROM")
        print("        memory. The file format is Intel Extended HEX.")
        print("-s      Read signature bytes.")
        print("-O      Read oscillator calibration byte. 'index' is optional.")
        print("--O#    User-defined oscillator calibration value.")
        print(
            "--Sf    Write oscillator cal. byte to FLASH memory. 'addr' is byte address."
        )
        print(
            "--Se    Write oscillator cal. byte to EEPROM memory. 'addr' is byte address."
        )
        print(
            "-e      Erase device. If applied with another programming parameter, the"
        )
        print("        device will be erased before any other programming takes place.")
        print(
            "-p      Program device; FLASH (f), EEPROM (e) or both (b). Corresponding"
        )
        print("        input files are required.")
        print(
            "-r      Read out device; FLASH (f), EEPROM (e) or both (b). Corresponding"
        )
        print("        output files are required")
        print(
            "-v      Verify device; FLASH (f), EEPROM (e) or both (b). Can be used with"
        )
        print("        -p or alone. Corresponding input files are required.")
        print("-l      Set lock byte. 'value' is an 8-bit hex. value.")
        print(
            "-L      Verify lock byte. 'value' is an 8-bit hex. value to verify against."
        )
        print("-y      Read back lock byte.")
        print("-f      Set fuse bytes. 'value' is a 16-bit hex. value describing the")
        print("        settings for the upper and lower fuse bytes.")
        print(
            "-E      Set extended fuse byte. 'value' is an 8-bit hex. value describing the"
        )
        print("        extend fuse settings.")
        print(
            "-F      Verify fuse bytes. 'value' is a 16-bit hex. value to verify against."
        )
        print("-G      Verify extended fuse byte. 'value' is an 8-bit hex. value to")
        print("        verify against.")
        print("-q      Read back fuse bytes.")
        print("-n      Send/receive encrypted hex files.")
        print("-x      Fill unspecified locations with a value (00-ff). The default is")
        print("        to not program locations not specified in the input files.")
        print(
            "--af    FLASH address range. Specifies the address range of operations. The"
        )
        print("        default is the entire FLASH. Byte addresses in hex.")
        print(
            "--ae    EEPROM address range. Specifies the address range of operations."
        )
        print("        The default is the entire EEPROM. Byte addresses in hex.")
        print(
            "-c      Select communication port; 'COM1' to 'COM8', '/dev/tty0', /dev/ttyUSB0."
        )
        print(
            "        Deprecated: It is suggested to use settings in the configuration file."
        )
        print("-b      Get revisions; hardware revision (h) and software revision (s).")
        print("-g      Silent operation.")
        print(
            "-z      No progress indicator. E.g. if piping to a file for log purposes."
        )
        print(
            "-Y      Calibrate internal RC oscillator(AVR057). 'addr' is byte address"
        )
        print("        this option to avoid the characters used for the indicator.")
        print("-h|-?   Help information (overrides all other settings).")
        print("")


"""
    Hex file utility classes and functions.
"""
import binascii

HEX_RECORD_LENGTH = 32


class HexRecord:
    """
    HexRecord class.
    Represents a line, or hex record, of a hex file.
    """

    def __init__(self):

        self._length = -1
        self._offset = -1
        self._type = -1
        self._checksum = -1
        self._data = bytearray(chr(0xFF).encode("iso-8859-1") * HEX_RECORD_LENGTH)

    def set_length(self, length):

        self._length = length

    def set_offset(self, offset):

        self._offset = offset

    def set_type(self, _type):

        self._type = _type

    def set_data(self, data):

        self._data = bytearray(data)

    def get_length(self):

        return self._length

    def get_offset(self):

        return self._offset

    def get_type(self):

        return self._type

    def get_data(self):

        return self._data

    def is_in_range(self, address):

        result = False
        if address >= self._offset and address < (self._offset + self._length):
            result = True
        return result

    def get_checksum(self):

        if self._checksum == -1:
            self.checksum()
        return self._checksum

    def checksum(self):

        self._checksum = self._length
        self._checksum += (self._offset >> 8) & 0xFF
        self._checksum += self._offset & 0xFF
        self._checksum += self._type

        for i in range(0, self._length):
            self._checksum += self._data[i]

        self._checksum = 0 - self._checksum
        self._checksum = self._checksum & 0xFF

        return self._checksum

    def from_string(self, hex_line):
        """
        Parses a line from a hex file.
        """

        if len(hex_line) < 11:
            raise RuntimeError(
                "Incorrect Hex file format, missing fields. "
                + "Line from file (%s)" % (hex_line.strip())
            )

        if hex_line[0] != ":":
            raise RuntimeError(
                "Incorrect Hex file format, does not start with a colon. "
                + "Line from file (%s)" % (hex_line.strip())
            )

        self._length = int(hex_line[1:3], 16)
        self._offset = int(hex_line[3:7], 16)
        self._type = int(hex_line[7:9], 16)

        if len(hex_line) < (self._length * 2 + 11):
            raise RuntimeError(
                "Incorrect Hex file format, missing field. "
                + "Line from file (%s)" % (hex_line.strip())
            )

        checksum = self._length
        checksum += (self._offset >> 8) & 0xFF
        checksum += self._offset & 0xFF
        checksum += self._type

        adata = hex_line[9 : (self._length * 2 + 9)]
        if len(adata) % 2 != 0:
            raise RuntimeError(
                "Incorrect Hex file format, invalid data. "
                + "Line from file (%s)" % (hex_line.strip())
            )

        bdata = binascii.a2b_hex(adata)
        j = 0
        for b in bdata:
            checksum += b
            self._data[j] = b
            j += 1

        checksum += int(hex_line[-2:], 16)
        checksum &= 0xFF
        if checksum != 0:
            raise RuntimeError(
                "Incorrect Hex file format, invalid checksum. "
                + "Line from file (%s)" % (hex_line.strip())
            )

    def __str__(self):
        """
        Returns a hex file line string.
        """

        if self._checksum == -1:
            self.checksum()

        result = ":%02X%04X%02X" % (self._length, self._offset, self._type)

        for i in range(0, self._length):
            result = "%s%02X" % (result, self._data[i])

        result = "%s%02X" % (result, (self._checksum & 0xFF))
        return result


class HexFile:
    """
    HexFile class.
    A class to represent a hex file. It contains
    """

    def __init__(self, buffersize, value=0xFF):

        self.__data = bytearray(chr((value & 0xFF)).encode("iso-8859-1") * buffersize)
        self.__start = -1
        self.__end = -1
        self.__size = buffersize

    def _write_record(self, fp, hex_rec):

        # fp.write('%02X\n' % str(hex_rec))
        fp.write("%s\n" % str(hex_rec))

    def _parse_record(self, hex_line):  # returns HexRecord

        hex_rec = HexRecord()
        hex_rec.from_string(hex_line.strip())
        return hex_rec

    def read_file(self, file_name):

        fp = open(file_name, "r")
        base_address = 0
        self.__start = self.__size
        self.__end = 0
        lines = fp.readlines()
        for line in lines:

            progress(".")

            rec = self._parse_record(line.strip())
            if rec.get_type() == 0x00:
                if (base_address + rec.get_offset() + rec.get_length()) > self.__size:
                    raise RuntimeError("Hex file defines data outside buffer limits.")

                for data_pos in range(0, rec.get_length()):
                    self.__data[base_address + rec.get_offset() + data_pos] = rec._data[
                        data_pos
                    ]

                if base_address + rec.get_offset() < self.__start:
                    self.__start = base_address + rec.get_offset()

                if base_address + rec.get_offset() + rec.get_length() > self.__end:
                    self.__end = base_address + rec.get_offset() + rec.get_length() - 1

            elif rec.get_type() == 0x01:
                fp.close()
                progress("\n")
                return
            elif rec.get_type() == 0x02:
                base_address = (rec._data[0] << 8) | rec._data[1]
                base_address <<= 4
            elif rec.get_type() == 0x03:
                pass
            elif rec.get_type() == 0x04:
                base_address = (rec._data[0] << 8) | rec._data[1]
                base_address <<= 16
            elif rec.get_type() == 0x05:
                pass
            else:
                raise RuntimeError(
                    "Incorrect Hex file format, unsupported format. "
                    + "Line from file (%s)" % (line)
                )

        raise RuntimeError(
            "Premature EOF encountered. " + "Make sure file contains an EOF record."
        )

    def write_file(self, file_name):

        fp = open(file_name, "w")

        base_address = self.__start & ~0xFFFF
        self._offset = self.__start & 0xFFFF

        rec = HexRecord()
        rec.set_length(2)
        rec.set_offset(0)
        rec.set_type(0x02)
        rec._data[1] = 0x00
        rec._data[0] = base_address >> 12
        rec.checksum()
        self._write_record(fp, rec)

        rec = HexRecord()
        rec.set_length(self.__size)
        data_pos = 0
        while base_address + self._offset + data_pos <= self.__end:
            rec._data[data_pos] = self.__data[base_address + self._offset + data_pos]
            data_pos += 1

            # check if we need to write out the current data record
            #     reached 64k boundary or
            #     data record full or
            #     end of used range reached
            if (
                self._offset + data_pos >= 0x10000
                or data_pos >= HEX_RECORD_LENGTH
                or base_address + self._offset + data_pos > self.__end
            ):
                rec.set_length(data_pos)
                rec.set_offset(self._offset)
                rec.set_type(0x00)

                if data_pos % 256 == 0:
                    progress(".")

                rec.checksum()
                self._write_record(fp, rec)

                self._offset += data_pos
                data_pos = 0

            # check if we have passed a 64k boundary
            if self._offset + data_pos >= 0x10000:
                # update address pointers
                self._offset -= 0x10000
                base_address += 0x10000

                # write new base address record to hex file
                rec.set_length(2)
                rec.set_offset(0)
                rec.set_type(0x02)
                # give 4k page index
                rec._data[0] = base_address >> 12
                rec._data[1] = 0x00

                rec.checksum()
                self._write_record(fp, rec)

        # write EOF record
        rec.set_length(0)
        rec.set_offset(0)
        rec.set_type(0x01)

        rec.checksum()
        self._write_record(fp, rec)

        fp.close()
        progress("\n")

    def set_used_range(self, start, end):

        if start < 0 or end >= self.__size or start > end:
            raise RuntimeError(
                "Invalid range! Start must be 0 or greater, "
                + "end must be inside allowed memory range."
            )
        self.__start = start
        self.__end = end

    def clear_all(self, value=0xFF):

        for i in range(0, self.__size):
            self.__data[i] = value & 0xFF

    def get_range_start(self):

        return self.__start

    def get_range_end(self):

        return self.__end

    def get_data(self, address):  # returns from byte array

        if address < 0 or address >= self.__size:
            raise RuntimeError("Address outside valid range!")
        return self.__data[address]

    def set_data(self, address, value):

        if type(value) != bytes or len(value) != 1:
            raise RuntimeError("HexFile.set_data() invalid value.")

        if address < 0 or address >= self.__size:
            raise RuntimeError("Address outside valid range!")
        self.__data[address] = value[0]

    def get_size(self):

        return self.__size


"""
    AVR programmer and bootloader
"""


class AVRProgrammer:
    """
    AVRProgrammer class.
    Singleton class that represents the programmer. It attempts
    to sync with the device bootloader and determine the bootloader
    type. If successful, a AVRBootloader is instantiated and
    subsequently used as the main interface point.
    """

    def __init__(self, port):
        self.__port = port

    def instance(port=None):

        for _ in range(0, 10):  # sync with programmer
            port.write(chr(27).encode("iso-8859-1"))
            port.flush()

        port.write(b"S")  # get programmer ID
        port.flush()

        pid = port.read(7)
        avrlog(LOG_DEBUG, "Read programmer ID: (%s)" % pid)
        if pid == b"AVRBOOT" or pid == b"CATERIN":
            return AVRBootloader.instance(port)
        else:
            raise RuntimeError("AVR programmer not found.")

    instance = staticmethod(instance)


class AVRBootloader:

    def __init__(self, port):
        self.__port = port
        self.__page_size = -1

    def get_page_size(self):

        return self.__page_size

    def set_page_size(self, size):

        self.__page_size = size

    def enter_programming_mode(self):

        return True

    def leave_programming_mode(self):

        # Not 100% certain this is correct
        self.__port.write(b"E")
        self.__port.flush()

        if self.__port.read(1) != b"\r":
            result = False
            avrlog(LOG_ERR, "Leave programming mode failed! Programmer did not ack.")

        return True

    def chip_erase(self):

        result = True
        self.__port.write(b"e")
        self.__port.flush()

        if self.__port.read(1) != b"\r":
            result = False
            avrlog(LOG_ERR, "Chip erase failed! Programmer did not ack.")

        return result

    def rc_calibrate(self):

        return (False, "")

    def read_osccal(self, pos):  # @UnusedVariable

        return (False, 0)

    def read_signature(self):

        self.__port.write(b"s")
        self.__port.flush()

        sig0 = None
        sig1 = None
        sig2 = None
        sigs = self.__port.read(3)
        if len(sigs) == 3:
            sig2 = sigs[0]
            sig1 = sigs[1]
            sig0 = sigs[2]
        return (sig0, sig1, sig2)

    def check_signature(self, sig0, sig1, sig2):

        result = True
        chk0, chk1, chk2 = self.read_signature()
        if chk0 != sig0 or chk1 != sig1 or chk2 != sig2:
            result = False
            avrlog(
                LOG_ERR,
                "Signature does not match selected device: "
                + "0x%02x 0x%02x 0x%02x vs %02x %02x %02x"
                % ((chk0), (chk1), (chk2), (sig0), (sig1), (sig2)),
            )
        return result

    def write_flash_byte(self, address, value):

        if type(value) == int and value < 0x100 and type(address) == int:
            self.set_address(address >> 1)  # Flash operations use word addresses.
            if address & 0x01:
                value = (value << 8) | 0x00FF
            else:
                value = value | 0xFF00

            self.write_flash_low_byte(value & 0xFF)
            self.write_flash_high_byte(value >> 8)

            self.set_address(address >> 1)
            self.write_flash_page()
        else:
            raise RuntimeError(
                "AVRBootloader.write_flash_bytes received %s:%s, "
                % (str(type(address)), str(type(value)))
                + "expected IntType"
            )

    def write_eeprom_byte(self, address, value):

        if type(value) == int and value < 0x100 and type(address) == int:
            self.set_address(address)
            result = True
            self.__port.write(b"D")
            self.__port.write(chr(value).encode("iso-8859-1"))
            self.__port.flush()

            if self.__port.read(1) != b"\r":
                result = False
                avrlog(
                    LOG_ERR, "Write eeprom byte failed! " + "Programmer did not ack."
                )

            return result
        else:
            raise RuntimeError(
                "AVRBootloader.write_flash_bytes received %s:%s, "
                % (str(type(address)), str(type(value)))
                + "expected IntType"
            )

    def write_flash(self, hex_file):

        if self.__page_size == -1:
            raise RuntimeError("Programmer page size not set!")

        self.__port.write(b"b")
        self.__port.flush()

        if self.__port.read(1) == b"Y":
            avrlog(LOG_DEBUG, "Using block mode...")
            return self.write_flash_block(hex_file)

        start = hex_file.get_range_start()
        end = hex_file.get_range_end()

        # check autoincrement support
        self.__port.write(b"a")
        self.__port.flush()

        autoincrement = False
        if self.__port.read(1) == b"Y":
            autoincrement = True

        self.set_address(start >> 1)  # flash operations use word addresses

        address = start
        if address & 1:
            self.write_flash_low_byte(0xFF)
            self.write_flash_high_byte(hex_file.get_data(address))
            address += 1
            if address % self.__page_size == 0 or address > end:
                self.set_address((address - 2) >> 1)
                self.write_flash_page()
                self.set_address(address >> 1)

        while (end - address + 1) >= 2:
            if not autoincrement:
                self.set_address(address >> 1)
            self.write_flash_low_byte(hex_file.get_data(address))
            self.write_flash_high_byte(hex_file.get_data(address + 1))
            address += 2

            if address % 256 == 0:
                progress(".")

            if address % self.__page_size == 0 or address > end:
                self.set_address((address - 2) >> 1)
                self.write_flash_page()
                self.set_address(address >> 1)

        if address == end:
            self.write_flash_low_byte(hex_file.get_data(address))
            self.write_flash_high_byte(0xFF)
            address += 2
            self.set_address((address - 2) >> 1)
            self.write_flash_page()

        progress("\n")
        return True

    def write_flash_block(self, hex_file):

        # Get block size assuming the 'b' command was just ack'ed with a 'Y'
        block_size = ((self.__port.read(1)[0]) << 8) | (self.__port.read(1)[0])

        start = hex_file.get_range_start()
        end = hex_file.get_range_end()

        address = start
        if address & 1:
            self.set_address(address >> 1)  # Flash operations use word addresses

            # Use only high byte
            self.write_flash_low_byte(0xFF)
            self.write_flash_high_byte(hex_file.get_data(address))
            address += 1

            if address % self.__page_size == 0 or address > end:
                self.set_address((address - 2) >> 1)
                self.write_flash_page()
                self.set_address(address >> 1)

        if (address % block_size) > 0:
            byte_count = block_size - (address & block_size)

            if (address + byte_count - 1) > end:
                byte_count = end - address + 1
                byte_count &= ~0x01  # Adjust to word count

            if byte_count > 0:
                self.set_address(address >> 1)

                self.__port.write(b"B")
                self.__port.write(chr((byte_count >> 8) & 0xFF).encode("iso-8859-1"))
                self.__port.write(chr(byte_count & 0xFF).encode("iso-8859-1"))
                self.__port.write(b"F")

                while byte_count > 0:
                    self.__port.write(hex_file.get_data(address).encode("iso-8859-1"))
                    address += 1
                    byte_count -= 1

                if self.__port.read(1) != b"\r":
                    raise RuntimeError(
                        "Writing Flash block failed! "
                        + "Programmer did not return CR after B..F command"
                    )
                progress(".")

        while (end - address + 1) >= block_size:

            byte_count = block_size

            self.set_address(address >> 1)

            self.__port.write(b"B")
            self.__port.write(chr((byte_count >> 8) & 0xFF).encode("iso-8859-1"))
            self.__port.write(chr(byte_count & 0xFF).encode("iso-8859-1"))
            self.__port.write(b"F")

            while byte_count > 0:
                self.__port.write(chr(hex_file.get_data(address)).encode("iso-8859-1"))
                address += 1
                byte_count -= 1

            if self.__port.read(1) != b"\r":
                raise RuntimeError(
                    "Writing Flash block failed! "
                    + "Programmer did not return CR after B..F command"
                )
            progress(".")

        if (end - address + 1) >= 1:

            byte_count = end - address + 1
            if byte_count & 1:
                byte_count += 1

            self.set_address(address >> 1)

            self.__port.write(b"B")
            self.__port.write(chr((byte_count >> 8) & 0xFF).encode("iso-8859-1"))
            self.__port.write(chr(byte_count & 0xFF).encode("iso-8859-1"))
            self.__port.write(b"F")

            while byte_count > 0:
                if address > end:
                    self.__port.write(chr(0xFF).encode("iso-8859-1"))
                else:
                    self.__port.write(
                        chr(hex_file.get_data(address)).encode("iso-8859-1")
                    )
                address += 1
                byte_count -= 1

            if self.__port.read(1) != b"\r":
                raise RuntimeError(
                    "Writing Flash block failed! "
                    + "Programmer did not return CR after B..F command"
                )
            progress(".")

        progress("\n")

        return True

    def read_flash(self, hex_file):

        if self.__page_size == -1:
            raise RuntimeError("Programmer page size is not set.")

        self.__port.write(b"b")
        self.__port.flush()

        if self.__port.read(1) == b"Y":
            avrlog(LOG_DEBUG, "Read flash: using block mode...")
            return self.read_flash_block(hex_file)

        start = hex_file.get_range_start()
        end = hex_file.get_range_end()

        self.__port.write(b"a")
        self.__port.flush()

        auto_increment = False
        if self.__port.read(1) == b"Y":
            auto_increment = True

        self.set_address(start >> 1)

        address = start
        if address & 1:
            self.__port.write(b"R")
            self.__port.flush()

            hex_file.set_data(address, self.__port.read(1))  # High byte
            self.__port.read(1)  # Don't use low byte
            address += 1

        while (end - address + 1) >= 2:
            if not auto_increment:
                self.set_address(address >> 1)

            self.__port.write(b"R")
            self.__port.flush()

            hex_file.set_data(address + 1, self.__port.read(1))
            hex_file.set_data(address, self.__port.read(1))
            address += 2

            if address % 256 == 0:
                progress(".")

        if address == end:
            self.__port.write(b"R")
            self.__port.flush()

            self.__port.read(1)
            hex_file.set_data(address, self.__port.read(1))

        progress("\n")

    def read_flash_block(self, hex_file):

        # Get block size assuming the 'b' command was just ack'ed with a 'Y'
        block_size = ((self.__port.read(1)[0]) << 8) | (self.__port.read(1)[0])

        start = hex_file.get_range_start()
        end = hex_file.get_range_end()

        address = start
        if address & 1:
            self.set_address(address >> 1)  # Flash operations use word addresses

            self.__port.write(b"R")
            self.__port.flush()

            hex_file.set_data(address, self.__port.read(1))  # Save high byte
            self.__port.read(1)  # Skip low byte
            address += 1

        if (address % block_size) > 0:
            byte_count = block_size - (address % block_size)

            if (address + byte_count - 1) > end:
                byte_count = end - address + 1
                byte_count &= ~0x01

            if byte_count > 0:
                self.set_address(address >> 1)

                # Start Flash block read
                self.__port.write(b"g")
                self.__port.write(chr((byte_count >> 8) & 0xFF).encode("iso-8859-1"))
                self.__port.write(chr(byte_count & 0xFF).encode("iso-8859-1"))
                self.__port.write(b"F")

                while byte_count > 0:
                    hex_file.set_data(address, self.__port.read(1))
                    address += 1
                    byte_count -= 1

                progress(".")

        while (end - address + 1) >= block_size:
            byte_count = block_size

            self.set_address(address >> 1)

            # Start Flash block read
            self.__port.write(b"g")
            self.__port.write(chr((byte_count >> 8) & 0xFF).encode("iso-8859-1"))
            self.__port.write(chr(byte_count & 0xFF).encode("iso-8859-1"))
            self.__port.write(b"F")

            while byte_count > 0:
                hex_file.set_data(address, self.__port.read(1))
                address += 1
                byte_count -= 1

            progress(".")

        if (end - address + 1) >= 1:
            byte_count = end - address + 1
            if byte_count & 1:
                byte_count += 1

            self.set_address(address >> 1)

            # Start Flash block read
            self.__port.write(b"g")
            self.__port.write(chr((byte_count >> 8) & 0xFF).encode("iso-8859-1"))
            self.__port.write(chr(byte_count & 0xFF).encode("iso-8859-1"))
            self.__port.write(b"F")

            while byte_count > 0:
                if address > end:
                    self.__port.read(1)
                else:
                    hex_file.set_data(address, self.__port.read(1))

                address += 1
                byte_count -= 1

            progress(".")

        progress("\n")

        return True

    def write_eeprom(self, hex_file):

        self.__port.write(b"b")
        self.__port.flush()

        if self.__port.read(1) == b"Y":
            avrlog(LOG_DEBUG, "Write EEPROM using block mode...")

        start = hex_file.get_range_start()
        end = hex_file.get_range_end()

        self.__port.write(b"a")
        self.__port.flush()

        auto_increment = False
        if self.__port.read(1) == b"Y":
            auto_increment = True

        self.set_address(start)

        address = start
        while address <= end:

            if not auto_increment:
                self.set_address(address)

            self.__port.write(b"D")
            self.__port.write(hex_file.get_data(address).encode("iso-8859-1"))
            self.__port.flush()

            if self.__port.read(1) != b"\r":
                raise RuntimeError(
                    "Writing byte to EEPROM failed! "
                    + "Programmer did not ack command."
                )
            if address % 256 == 0:
                progress(".")

            address += 1

        progress("\n")

        return True

    def write_eeprom_block(self, hex_file):

        # Get block size assuming the 'b' command was just ack'ed with a 'Y'
        block_size = (self.__port.read(1)[0] << 8) | self.__port.read(1)[0]

        start = hex_file.get_range_start()
        end = hex_file.get_range_end()

        address = start
        while address <= end:
            byte_count = block_size
            if (address + byte_count - 1) > end:
                byte_count = end - address + 1

            self.set_address(address)

            self.__port.write(b"B")
            self.__port.write(chr((byte_count >> 8) & 0xFF).encode("iso-8859-1"))
            self.__port.write(chr(byte_count & 0xFF).encode("iso-8859-1"))
            self.__port.write(b"E")

            while byte_count > 0:
                self.__port.write(hex_file.get_data(address).encode("iso-8859-1"))
                self.__port.flush()

                address += 1
                byte_count -= 1

            if self.__port.read(1) != b"\r":
                raise RuntimeError(
                    "Writing EEPROM block failed! "
                    + "Programmer did not ack B..E command."
                )

            progress(".")

        progress("\n")

        return True

    def read_eeprom(self, hex_file):

        self.__port.write(b"b")
        self.__port.flush()

        if self.__port.read(1) == b"Y":
            avrlog(LOG_DEBUG, "Read EEPROM: using block mode...")
            return self.read_eeprom_block(hex_file)

        start = hex_file.get_range_start()
        end = hex_file.get_range_end()

        self.__port.write(b"a")
        self.__port.flush()

        auto_increment = False
        if self.__port.read(1) == b"Y":
            auto_increment = True

        self.set_address(start)

        address = start
        while address <= end:
            if not auto_increment:
                self.set_address(address)

            self.__port.write(b"d")
            self.__port.flush()

            hex_file.set_data(address, self.__port.read(1))

            if address % 256 == 0:
                progress(".")

            address += 1

        progress("\n")

        return True

    def read_eeprom_block(self, hex_file):

        # Get block size assuming the 'b' command was just ack'ed with a 'Y'
        block_size = ((self.__port.read(1)[0]) << 8) | (self.__port.read(1)[0])

        start = hex_file.get_range_start()
        end = hex_file.get_range_end()

        address = start
        while address <= end:
            byte_count = block_size
            if (address + byte_count - 1) > end:
                byte_count = end - address + 1

            self.set_address(address)

            self.__port.write(b"g")
            self.__port.write(chr((byte_count >> 8) & 0xFF).encode("iso-8859-1"))
            self.__port.write(chr(byte_count & 0xFF).encode("iso-8859-1"))
            self.__port.write(b"E")

            while byte_count > 0:
                hex_file.set_data(address, self.__port.read(1))

                address += 1
                byte_count -= 1

            progress(".")

        progress("\n")

        return True

    def write_lock_bits(self, value):

        if type(value) == int and value < 0x100:
            self.__port.write(b"l")
            self.__port.write(chr(value & 0xFF).encode("iso-8859-1"))
            self.__port.flush()

            bits = self.__port.read(1)

            return (True, bits)
        else:
            raise RuntimeError(
                "AVRBootloader.write_lock_bits received %s, " % str(type(value))
                + "expected IntType"
            )

    def read_lock_bits(self):

        self.__port.write(b"r")
        self.__port.flush()

        bits = self.__port.read(1)

        return (True, (bits))

    def write_fuse_bits(self, bits):  # @UnusedVariable

        return False

    def read_fuse_bits(self):

        self.__port.write(b"N")
        self.__port.flush()

        highfuse = self.__port.read(1)[0]

        self.__port.write(b"F")
        self.__port.flush()

        lowfuse = self.__port.read(1)[0]

        bits = ((highfuse) << 8) | (lowfuse)

        return (True, bits)

    def write_extended_fuse_bits(self):

        return False

    def read_extended_fuse_bits(self):

        self.__port.write(b"Q")
        self.__port.flush()

        bits = self.__port.read(1)

        return (True, (bits))

    def programmer_software_version(self):

        self.__port.write(b"V")
        self.__port.flush()

        major = self.__port.read(1)
        minor = self.__port.read(1)

        return (True, major, minor)

    def programmer_hardware_version(self):

        return (False, 0, 0)

    def set_address(self, address):

        result = True
        if address < 0x10000:
            self.__port.write(b"A")
            self.__port.write(chr(((address >> 8) & 0xFF)).encode("iso-8859-1"))
            self.__port.write(chr(address & 0xFF).encode("iso-8859-1"))
            self.__port.flush()
        else:
            self.__port.write(b"H")
            self.__port.write(chr(((address >> 16) & 0xFF)).encode("iso-8859-1"))
            self.__port.write(chr(((address >> 8) & 0xFF)).encode("iso-8859-1"))
            self.__port.write(chr(address & 0xFF).encode("iso-8859-1"))
            self.__port.flush()

        if self.__port.read(1) != b"\r":
            result = False
            avrlog(LOG_ERR, "Setting address failed! " + "Programmer did not ack.")

        return result

    def write_flash_low_byte(self, value):

        if type(value) == int and value < 0x100:
            result = True
            self.__port.write(b"c")
            self.__port.write(chr(value).encode("iso-8859-1"))
            self.__port.flush()

            if self.__port.read(1) != b"\r":
                result = False
                avrlog(
                    LOG_ERR, "Write flash low byte failed! " + "Programmer did not ack."
                )

            return result
        else:
            raise RuntimeError(
                "AVRBootloader.write_flash_low_byte received %s, " % str(type(value))
                + "expected IntType"
            )

    def write_flash_high_byte(self, value):

        if type(value) == int and value < 0x100:
            result = True
            self.__port.write(b"C")
            self.__port.write(chr(value).encode("iso-8859-1"))
            self.__port.flush()

            if self.__port.read(1) != b"\r":
                result = False
                avrlog(
                    LOG_ERR,
                    "Write flash high byte failed! " + "Programmer did not ack.",
                )

            return result
        else:
            raise RuntimeError(
                "AVRBootloader.write_flash_high_byte received %s, " % str(type(value))
                + "expected IntType"
            )

    def write_flash_page(self):

        result = True
        self.__port.write(b"m")
        self.__port.flush()

        if self.__port.read(1) != b"\r":
            result = False
            avrlog(LOG_ERR, "Write flash page failed! Programmer did not ack.")

        return result

    def instance(port=None):

        return AVRBootloader(port)

    instance = staticmethod(instance)


"""
    AVR Device utility
"""
from os.path import exists, join
from os import pathsep
import xml.etree.ElementTree as ET

atmega32u4_xml = """<?xml version="1.0"?>
<AVRPART>
  <MEMORY>
    <PROG_FLASH>32768</PROG_FLASH>
    <EEPROM>1024</EEPROM>
    <BOOT_CONFIG>
      <NRWW_START_ADDR>$3800</NRWW_START_ADDR>
      <NRWW_STOP_ADDR>$3FFF</NRWW_STOP_ADDR>
      <PAGESIZE>64</PAGESIZE>
    </BOOT_CONFIG>
  </MEMORY>
  <FUSE>
    <EXTENDED>
    </EXTENDED>
  </FUSE>
  <ADMIN>
    <SIGNATURE>
      <ADDR000>$1E</ADDR000>
      <ADDR001>$95</ADDR001>
      <ADDR002>$87</ADDR002>
    </SIGNATURE>
  </ADMIN>
</AVRPART>
"""


class AVRDevice:
    """
    AVRDevice class.
    This is a class to represent an AVR device. XML files that
    are part of the AVR Studio installation are used to provide
    the device schema. An AVRDevice object is instantiated given
    the device name in order to find and parse the device's XML
    file.
    """

    def __init__(self, device_name):

        self._device_name = device_name
        self._flash_size = -1
        self._eeprom_size = -1
        self._has_fuse_bits = False
        self._has_extended_fuse_bits = False
        self._sig0 = -1
        self._sig1 = -1
        self._sig2 = -1
        self._page_size = -1
        self._nrww_size = -1

    def get_device_name(self):

        return self._device_name

    def get_flash_size(self):

        return self._flash_size

    def get_eeprom_size(self):

        return self._eeprom_size

    def get_page_size(self):

        return self._page_size

    def get_nrww_size(self):

        return self._nrww_size

    def get_nrww_pages(self):

        return self._nrww_size * 2 / self._page_size

    def get_total_pages(self):

        return self._flash_size / self._page_size

    def get_fuse_status(self):

        return self._has_fuse_bits

    def get_ext_fuse_status(self):

        return self._has_extended_fuse_bits

    def get_signature(self):

        return (self._sig0, self._sig1, self._sig2)

    def read_avr_parameters(self, search_path):

        if len(self._device_name) <= 0:
            raise RuntimeError("A device name must be specified.")

        file_name = ""
        paths = search_path.split(pathsep)
        for path in paths:
            if exists(join(path, "%s.xml" % self._device_name)):
                file_name = join(path, "%s.xml" % self._device_name)

        if len(file_name) > 0 or self._device_name == "ATmega32U4":
            avrlog(LOG_DEBUG, "found file: %s" % file_name)

            if self._device_name == "ATmega32U4":
                tree = ET.ElementTree(ET.fromstring(atmega32u4_xml))
            else:
                tree = ET.parse(file_name)
            if tree != None:
                memory = tree.getroot().find("MEMORY")
                if memory != None:
                    prog_flash = memory.find("PROG_FLASH")
                    if prog_flash != None and prog_flash.text.isdigit():
                        self._flash_size = int(prog_flash.text)
                    else:
                        raise RuntimeError(
                            "Flash size not found for %s" % self._device_name
                        )
                    eeprom = memory.find("EEPROM")
                    if eeprom != None and eeprom.text.isdigit():
                        self._eeprom_size = int(eeprom.text)
                    else:
                        raise RuntimeError(
                            "EEPROM size not found for %s" % self._device_name
                        )
                    boot_cfg = memory.find("BOOT_CONFIG")
                    if boot_cfg != None:
                        page_size = boot_cfg.find("PAGESIZE")
                        if page_size != None and page_size.text.isdigit():
                            self._page_size = int(page_size.text) << 1
                        nrww_start = -1
                        nrww_stop = -1
                        nrww_start_addr = boot_cfg.find("NRWW_START_ADDR")
                        if nrww_start_addr != None and len(nrww_start_addr.text) > 2:
                            nrww_start = int(nrww_start_addr.text[1:], 16)
                        nrww_stop_addr = boot_cfg.find("NRWW_STOP_ADDR")
                        if nrww_stop_addr != None and len(nrww_stop_addr.text) > 2:
                            nrww_stop = int(nrww_stop_addr.text[1:], 16)
                        if nrww_start > 0 and nrww_stop > nrww_start:
                            self._nrww_size = nrww_stop - nrww_start + 1
                else:
                    raise RuntimeError(
                        "Memory configuration not found in %s.xml." % self._device_name
                    )
                fuse = tree.getroot().find("FUSE")
                if fuse != None:
                    self._has_fuse_bits = True
                    ext_fuse = fuse.find("EXTENDED")
                    if ext_fuse != None:
                        self._has_extended_fuse_bits = True
                else:
                    avrlog(
                        LOG_DEBUG, "Fuse bits not supported on %s" % self._device_name
                    )
                admin = tree.getroot().find("ADMIN")
                if admin != None:
                    sig_sect = admin.find("SIGNATURE")
                    if sig_sect != None:
                        addr0 = sig_sect.find("ADDR000")
                        if addr0 != None and len(addr0.text) == 3:
                            self._sig0 = int(addr0.text[1:], 16)
                        else:
                            raise RuntimeError(
                                "Signature 0 section not found in %s.xml."
                                % self._device_name
                            )
                        addr1 = sig_sect.find("ADDR001")
                        if addr1 != None and len(addr1.text) == 3:
                            self._sig1 = int(addr1.text[1:], 16)
                        else:
                            raise RuntimeError(
                                "Signature 1 section not found in %s.xml."
                                % self._device_name
                            )
                        addr2 = sig_sect.find("ADDR002")
                        if addr2 != None and len(addr2.text) == 3:
                            self._sig2 = int(addr2.text[1:], 16)
                        else:
                            raise RuntimeError(
                                "Signature 2 section not found in %s.xml."
                                % self._device_name
                            )
                    else:
                        raise RuntimeError(
                            "Signature section not found in %s.xml." % self._device_name
                        )
                else:
                    raise RuntimeError(
                        "Admin section not found in %s.xml." % self._device_name
                    )
            else:
                raise RuntimeError("Error parsing %s.xml." % self._device_name)
        else:
            raise RuntimeError("%s XML file not found." % self._device_name)


"""
    AVR Loader main
"""
import sys  # @Reimport
import configparser
import traceback

"""
    This module is invoked from the command line to start the
    application that interfaces with the AVR device bootloader.
    See the JobInfo class for command line parameter documentation.
"""
if __name__ == "__main__":

    openlog("avrloader", LOG_PID, LOG_DAEMON)

    home_dir = sys.argv[0]
    slash_pos = sys.argv[0].rfind(os.sep)
    if slash_pos == -1:
        home_dir = "."
    else:
        home_dir = sys.argv[0][:slash_pos]

    parser = configparser.ConfigParser()
    cfg_file_name = "%s%savrloader.cfg" % (home_dir, os.sep)
    parser.read(cfg_file_name)

    try:
        log_level = eval("%s" % parser.get("Logging", "level"))
        setlogmask(LOG_UPTO(log_level))
    except:
        traceback.print_exc()
        setlogmask(LOG_UPTO(LOG_ERR))

    try:
        j = JobInfo()
        j.parse_command_line(sys.argv)
        if len(j.com_port_name) == 0:
            device = parser.get("Communication", "device")
            baud = parser.getint("Communication", "baud")
            timeout = parser.getfloat("Communication", "timeout")
            j.set_comms(device, baud, timeout)
        j.do_job()
    except RuntimeError as r_exc:
        avrlog(LOG_ERR, r_exc.message)
    except:
        avrlog(LOG_ERR, traceback.format_exc().replace("\n", "; "))
    closelog()
