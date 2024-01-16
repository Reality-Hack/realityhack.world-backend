# based on https://github.com/Reality-Hack/realityhack.world/blob/4e87c3a49941cb971b3b42113de30ffb50f5bcfb/src/python/hardware_qr.py

import base64
import os
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction
from PIL import Image

from infrastructure.models import Hardware, HardwareDevice

from ...qr_generator import QRGenerator


class Command(BaseCommand):  # pragma: no cover
    help = "Generates QR codes for hardware devices"

    def add_arguments(self, parser):
        parser.add_argument("--output", type=Path, required=False, default=os.path.join(settings.MEDIA_ROOT, "qr_codes"))


    @transaction.atomic
    def handle(self, *args, **kwargs):  # noqa: C901        
        hardware_devices = [(i, hd)
                            for h in Hardware.objects.all()
                            for i, hd in enumerate(HardwareDevice.objects.filter(hardware=h))]

        codes = [
            (f"{x.hardware.name}: {i + 1}",
           "S" + x.serial or "I" + x.id)
            for i, x in hardware_devices]

        out_dir = kwargs["output"]
        if not os.path.exists(out_dir):
            os.mkdir(out_dir)

        generator = QRGenerator(Image.open(os.path.join(settings.MEDIA_ROOT, "grid.png")))
        for i, page in enumerate(generator.fill_pages(codes)):
            page.save(f"{out_dir}/page_{i}.png","PNG")
