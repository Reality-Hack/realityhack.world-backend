from django.core.management.base import BaseCommand

from infrastructure.models import Hardware, HardwareDevice

class Command(BaseCommand):  # pragma: no cover
    help = "Given a hardware ID, generate the HardwareDevice Serial using a string key and sequential numbering from 1 to n (where n is the number of devices for that hardware)"
    
    def add_arguments(self, parser):
        parser.add_argument('hardware_id', type=str, help='The ID of the hardware to generate a serial for')
        parser.add_argument('key', type=str, help='The key to use for the serial')
   
    def handle(self, *args, **kwargs):
        hardware_id = kwargs['hardware_id']
        key = kwargs['key']
        hardware = Hardware.objects.get(id=hardware_id)
        devices = HardwareDevice.objects.filter(hardware=hardware)
        for i, device in enumerate(devices):
            device.serial = f"{key}-{i+1}"
            device.save()
        print(f"Updated {len(devices)} devices for {hardware.name}")
