import pydicom
from pydicom.dataset import Dataset, FileMetaDataset
from pydicom.uid import generate_uid, ExplicitVRLittleEndian
import datetime
import os
from pathlib import Path
from faker import Faker
import numpy as np
import logging

try:
    from PIL import Image, ImageDraw, ImageFont
    HAS_PILLOW = True
except ImportError:
    HAS_PILLOW = False

def create_study_files(output_dir: str, num_images: int, overrides: dict, generate_pixels: bool = True, jumble_body_part: bool = False):
    logging.info(f"DICOM Generator: Starting study generation in {output_dir}")
    
    fake = Faker()
    
    # --- Study-Level Data ---
    study_instance_uid = overrides.get('StudyInstanceUID', generate_uid())
    patient_name = overrides.get('PatientName', fake.name().replace(" ", "^"))
    patient_id = overrides.get('PatientID', '12345678')
    accession_number = overrides.get('AccessionNumber', 'ACC12345678')
    study_date = overrides.get('StudyDate', datetime.date.today().strftime("%Y%m%d"))
    study_time = overrides.get('StudyTime', datetime.datetime.now().strftime("%H%M%S"))
    chosen_modality = overrides.get('Modality', 'CT')
    study_description = overrides.get('StudyDescription', f"Generated {chosen_modality} Study")
    body_part_examined = overrides.get('BodyPartExamined', 'CHEST')

    study_output_path = Path(output_dir)
    study_output_path.mkdir(parents=True, exist_ok=True)
    
    imaging_series_uid = generate_uid()
    generated_files = []

    for i in range(num_images):
        instance_num = i + 1
        ds = Dataset()
        ds.file_meta = FileMetaDataset()
        ds.file_meta.TransferSyntaxUID = ExplicitVRLittleEndian

        ds.PatientName = patient_name
        ds.PatientID = patient_id
        ds.AccessionNumber = accession_number
        ds.StudyInstanceUID = study_instance_uid
        ds.SeriesInstanceUID = imaging_series_uid
        ds.SOPInstanceUID = generate_uid()
        # A CT Image Storage SOP Class
        ds.SOPClassUID = "1.2.840.10008.5.1.4.1.1.2"
        ds.Modality = chosen_modality
        ds.StudyDescription = study_description
        ds.BodyPartExamined = body_part_examined
        ds.InstanceNumber = str(instance_num)
        ds.StudyDate, ds.StudyTime = study_date, study_time
        ds.SeriesDate, ds.SeriesTime = study_date, study_time
        ds.ContentDate, ds.ContentTime = study_date, study_time
        
        # Add any other overrides passed in
        for key, value in overrides.items():
            setattr(ds, key, value)
            
        if generate_pixels:
            ds.Rows, ds.Columns = 512, 512
            ds.BitsAllocated, ds.BitsStored, ds.HighBit = 16, 12, 11
            ds.PixelRepresentation = 0
            ds.PhotometricInterpretation = "MONOCHROME2"
            ds.SamplesPerPixel = 1
            # Window Center and Width for good default display
            ds.WindowCenter = "40"
            ds.WindowWidth = "400"

            if HAS_PILLOW:
                from PIL import Image, ImageDraw, ImageFont  # Ensure ImageFont is imported here
                # --- Generate Plausible Pixel Data with Pillow ---
                width, height = ds.Columns, ds.Rows
                
                # Create a black image
                image = Image.new('L', (width, height))
                draw = ImageDraw.Draw(image)
                
                # Draw a simple phantom (e.g., a circle)
                draw.ellipse([(50, 50), (462, 462)], fill=128, outline=255, width=5)
                draw.rectangle([(200,200), (312,312)], fill=200, width=0)

                # Burn in text
                try:
                    font = ImageFont.truetype("DejaVuSans.ttf", 20)
                except IOError:
                    font = ImageFont.load_default()

                draw.text((10, 10), str(ds.PatientName), font=font, fill=255)
                draw.text((10, 35), f"MRN: {ds.PatientID}", font=font, fill=255)
                draw.text((10, 60), f"Acc: {ds.AccessionNumber}", font=font, fill=255)
                draw.text((10, height - 30), f"Img: {ds.InstanceNumber}/{num_images}", font=font, fill=255)

                # Convert to numpy array and scale to 12-bit
                pixel_array = np.array(image, dtype=np.uint16) * 16 # Scale 8-bit (0-255) to 12-bit (0-4095)
                ds.PixelData = pixel_array.tobytes()

            else:
                # Fallback to random noise if Pillow is not installed
                logging.warning("Pillow not installed. Generating random pixel data.")
                pixel_array = np.random.randint(0, 4095, (ds.Rows, ds.Columns), dtype=np.uint16)
                ds.PixelData = pixel_array.tobytes()

        filepath = study_output_path / f"{chosen_modality}.{ds.SOPInstanceUID}.dcm"
        ds.save_as(filepath, write_like_original=False)
        generated_files.append(str(filepath.resolve()))

    logging.info(f"DICOM Generator: Finished. Generated {len(generated_files)} files.")
    return generated_files

# --- END OF FILE app/util/dicom_generator.py ---