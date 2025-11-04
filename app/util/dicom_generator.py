import pydicom
from pydicom.dataset import Dataset, FileMetaDataset
from pydicom.uid import generate_uid, ImplicitVRLittleEndian, PYDICOM_IMPLEMENTATION_UID, UID
import datetime
import random
from pathlib import Path
from faker import Faker
import numpy as np
import logging

try:
    from PIL import Image, ImageDraw, ImageFont
    HAS_PILLOW = True
except ImportError:
    HAS_PILLOW = False
    Image = None
    ImageDraw = None  
    ImageFont = None

def _infer_body_part_from_description(description: str) -> str:
    """
    Infer appropriate body part examined from study description.
    Returns DICOM-appropriate body part codes.
    """
    if not description:
        return 'CHEST'  # Default fallback
    
    desc_upper = description.upper()
    
    # Define body part mapping patterns - order matters (most specific first)
    body_part_patterns = [
        # Head/Brain - specific patterns first
        (['BRAIN', 'HEAD MR', 'HEAD CT', 'CRANIUM', 'INTRACRANIAL'], 'HEAD'),
        (['SKULL', 'CRANIAL', 'HEAD XRAY', 'HEAD X-RAY'], 'SKULL'),
        (['HEAD'], 'HEAD'),
        
        # Spine - specific regions first
        (['CERVICAL', 'C-SPINE', 'C SPINE', 'NECK SPINE', 'C1', 'C2', 'C3', 'C4', 'C5', 'C6', 'C7'], 'CSPINE'),
        (['LUMBAR', 'L-SPINE', 'L SPINE', 'LOWER SPINE', 'LUMBOSACRAL', 'L1', 'L2', 'L3', 'L4', 'L5'], 'LSPINE'),
        (['THORACIC', 'T-SPINE', 'T SPINE', 'DORSAL', 'T1', 'T2', 'T3', 'T4', 'T5', 'T6', 'T7', 'T8', 'T9', 'T10', 'T11', 'T12'], 'TSPINE'),
        (['SACRAL', 'SACRUM', 'COCCYX', 'TAILBONE'], 'SSPINE'),
        (['SPINE', 'SPINAL'], 'SPINE'),
        
        # Chest/Thorax
        (['CHEST', 'THORAX', 'THORACIC CAVITY'], 'CHEST'),
        (['LUNG', 'PULMONARY', 'RESPIRATORY'], 'LUNG'),
        (['HEART', 'CARDIAC', 'CORONARY'], 'HEART'),
        (['RIB', 'RIBS', 'COSTAL'], 'RIB'),
        
        # Abdomen/Pelvis - specific organs first
        (['LIVER', 'HEPATIC'], 'LIVER'),
        (['KIDNEY', 'RENAL', 'NEPHRO'], 'KIDNEY'),
        (['PANCREAS', 'PANCREATIC'], 'PANCREAS'),
        (['SPLEEN', 'SPLENIC'], 'SPLEEN'),
        (['BLADDER', 'VESICAL'], 'BLADDER'),
        (['PROSTATE', 'PROSTATIC'], 'PROSTATE'),
        (['UTERUS', 'UTERINE', 'OVARY', 'OVARIAN'], 'PELVIS'),
        (['ABDOMEN', 'ABDOMINAL', 'PERITONEAL'], 'ABDOMEN'),
        (['PELVIS', 'PELVIC', 'HIP', 'SACROILIAC'], 'PELVIS'),
        
        # Upper Extremities
        (['SHOULDER', 'SCAPULA', 'CLAVICLE', 'ACROMIOCLAVICULAR'], 'SHOULDER'),
        (['ARM', 'HUMERUS', 'UPPER ARM'], 'ARM'),
        (['ELBOW', 'OLECRANON'], 'ELBOW'),
        (['FOREARM', 'RADIUS', 'ULNA'], 'FOREARM'),
        (['WRIST', 'CARPAL'], 'WRIST'),
        (['HAND', 'FINGER', 'THUMB', 'METACARPAL', 'PHALANGE'], 'HAND'),
        
        # Lower Extremities
        (['THIGH', 'FEMUR', 'UPPER LEG'], 'THIGH'),
        (['KNEE', 'PATELLA', 'MENISCUS'], 'KNEE'),
        (['LEG', 'TIBIA', 'FIBULA', 'LOWER LEG', 'CALF'], 'LEG'),
        (['ANKLE', 'MALLEOLUS'], 'ANKLE'),
        (['FOOT', 'TOE', 'METATARSAL', 'CALCANEUS', 'HEEL'], 'FOOT'),
        
        # Neck (non-spine)
        (['NECK', 'CERVICAL SOFT TISSUE', 'THYROID'], 'NECK'),
        
        # Breast/Mammography
        (['BREAST', 'MAMMARY', 'MAMMOGRAM'], 'BREAST'),
        
        # Eye/Orbit
        (['EYE', 'ORBIT', 'ORBITAL', 'OPHTHALMIC'], 'EYE'),
        
        # Ear/Temporal
        (['EAR', 'TEMPORAL', 'AUDITORY'], 'EAR'),
        
        # Jaw/TMJ
        (['JAW', 'MANDIBLE', 'MAXILLA', 'TMJ'], 'JAW'),
        
        # Whole body or multiple regions
        (['WHOLE BODY', 'TOTAL BODY', 'FULL BODY'], 'WHOLEBODY'),
    ]
    
    # Check each pattern
    for keywords, body_part in body_part_patterns:
        for keyword in keywords:
            if keyword in desc_upper:
                return body_part
    
    # Default fallback
    return 'CHEST'

def _generate_medical_image(modality: str, body_part: str, width: int = 512, height: int = 512, slice_num: int = 1, total_slices: int = 1):
    """
    Generate modality-specific medical images with proper pixel encoding for PACS.
    Returns a numpy array with proper bit depth for the modality.
    """
    if not HAS_PILLOW:
        # Fallback to numpy arrays if Pillow not available
        import numpy as np
        if modality in ['DX', 'CR']:
            # 14-bit X-ray data
            return np.random.randint(0, 16383, (height, width), dtype=np.uint16)
        else:
            # 12-bit data for CT/MR
            return np.random.randint(0, 4095, (height, width), dtype=np.uint16)
    
    from PIL import Image, ImageDraw
    import numpy as np
    
    # Create base image
    image = Image.new('L', (width, height), color=0)  # Black background
    draw = ImageDraw.Draw(image)
    
    # Set random seed based on slice number for consistency
    random.seed(slice_num * 42)
    
    if modality in ['CT']:
        image = _generate_ct_image(image, draw, body_part, width, height, slice_num, total_slices)
    elif modality in ['MR']:
        image = _generate_mr_image(image, draw, body_part, width, height, slice_num, total_slices)
    elif modality in ['DX', 'CR']:
        image = _generate_xray_image(image, draw, body_part, width, height)
    elif modality in ['US']:
        image = _generate_ultrasound_image(image, draw, body_part, width, height)
    elif modality in ['NM', 'PT']:
        image = _generate_nuclear_image(image, draw, body_part, width, height)
    elif modality in ['MG']:
        image = _generate_mammogram_image(image, draw, width, height)
    else:
        # Default to CT-like appearance
        image = _generate_ct_image(image, draw, body_part, width, height, slice_num, total_slices)
    
    # Convert PIL image to numpy array with proper scaling
    pixel_array = np.array(image, dtype=np.uint16)
    
    # Scale to appropriate bit depth based on modality
    if modality in ['CT', 'MR']:
        # Scale 8-bit (0-255) to 12-bit (0-4095)
        pixel_array = np.clip(pixel_array * 16, 0, 4095).astype(np.uint16)
    elif modality in ['DX', 'CR']:
        # Scale 8-bit (0-255) to 14-bit (0-16383)
        pixel_array = np.clip(pixel_array * 64, 0, 16383).astype(np.uint16)
    elif modality in ['US']:
        # Ultrasound typically 8-bit but can be stored as 16-bit
        pixel_array = np.clip(pixel_array * 256, 0, 65535).astype(np.uint16)
    else:
        # Default 12-bit scaling
        pixel_array = np.clip(pixel_array * 16, 0, 4095).astype(np.uint16)
    
    return pixel_array

def _generate_ct_image(image, draw, body_part: str, width: int, height: int, slice_num: int, total_slices: int):
    """Generate CT-like cross-sectional anatomy."""
    
    center_x, center_y = width // 2, height // 2
    
    if body_part in ['HEAD', 'BRAIN']:
        # Brain/skull outline
        skull_radius = min(width, height) // 3
        draw.ellipse([center_x - skull_radius, center_y - skull_radius, 
                     center_x + skull_radius, center_y + skull_radius], fill=180, outline=220)
        
        # Brain tissue
        brain_radius = skull_radius - 15
        draw.ellipse([center_x - brain_radius, center_y - brain_radius,
                     center_x + brain_radius, center_y + brain_radius], fill=120, outline=140)
        
        # Ventricles (darker areas)
        vent_size = 20
        draw.ellipse([center_x - vent_size, center_y - vent_size//2,
                     center_x + vent_size, center_y + vent_size//2], fill=40)
        
    elif body_part in ['CHEST', 'HEART', 'LUNG']:
        # Chest outline (oval)
        chest_w, chest_h = width//2 - 30, height//2 - 50
        draw.ellipse([center_x - chest_w, center_y - chest_h,
                     center_x + chest_w, center_y + chest_h], fill=100, outline=150)
        
        # Lungs (darker areas on sides)
        lung_h = chest_h - 20
        draw.ellipse([center_x - chest_w + 20, center_y - lung_h,
                     center_x - 20, center_y + lung_h], fill=60, outline=80)  # Left lung
        draw.ellipse([center_x + 20, center_y - lung_h,
                     center_x + chest_w - 20, center_y + lung_h], fill=60, outline=80)  # Right lung
        
        # Heart (brighter area)
        heart_w, heart_h = 40, 50
        draw.ellipse([center_x - heart_w//2, center_y - heart_h//2,
                     center_x + heart_w//2, center_y + heart_h//2], fill=140)
        
        # Spine (bright vertical line)
        draw.ellipse([center_x - 15, center_y + chest_h//2,
                     center_x + 15, center_y + chest_h + 20], fill=200, outline=220)
        
    elif body_part in ['ABDOMEN', 'LIVER', 'KIDNEY']:
        # Abdominal outline
        abd_w, abd_h = width//2 - 40, height//2 - 40
        draw.ellipse([center_x - abd_w, center_y - abd_h,
                     center_x + abd_w, center_y + abd_h], fill=110, outline=140)
        
        # Liver (upper right)
        draw.ellipse([center_x + 10, center_y - abd_h + 10,
                     center_x + abd_w - 10, center_y - abd_h//3], fill=130)
        
        # Kidneys (posterior)
        kidney_w, kidney_h = 25, 40
        draw.ellipse([center_x - abd_w//2, center_y - kidney_h//2,
                     center_x - abd_w//2 + kidney_w, center_y + kidney_h//2], fill=120)  # Left kidney
        draw.ellipse([center_x + abd_w//2 - kidney_w, center_y - kidney_h//2,
                     center_x + abd_w//2, center_y + kidney_h//2], fill=120)  # Right kidney
        
        # Spine
        draw.ellipse([center_x - 15, center_y + abd_h//2,
                     center_x + 15, center_y + abd_h + 20], fill=200, outline=220)
        
    elif body_part in ['SPINE', 'LSPINE', 'CSPINE', 'TSPINE', 'SSPINE']:
        # Determine spinal region characteristics for CT
        if body_part == 'CSPINE':
            # Cervical spine - smaller, more delicate structures
            vert_w, vert_h = 40, 28
            canal_w, canal_h = 18, 22
            transverse_size = 20
        elif body_part == 'TSPINE':
            # Thoracic spine - medium size, rib attachments
            vert_w, vert_h = 50, 35
            canal_w, canal_h = 20, 25
            transverse_size = 25
        elif body_part == 'LSPINE':
            # Lumbar spine - largest vertebrae
            vert_w, vert_h = 65, 45
            canal_w, canal_h = 22, 28
            transverse_size = 30
        else:
            # Generic spine
            vert_w, vert_h = 60, 40
            canal_w, canal_h = 20, 25
            transverse_size = 25
        
        # Vertebral body (bright - bone density ~200-300 HU)
        draw.ellipse([center_x - vert_w//2, center_y - vert_h//2,
                     center_x + vert_w//2, center_y + vert_h//2], fill=190, outline=210)
        
        # Cortical bone rim (brighter)
        draw.ellipse([center_x - vert_w//2, center_y - vert_h//2,
                     center_x + vert_w//2, center_y + vert_h//2], outline=220, width=2)
        
        # Posterior elements - pedicles, laminae
        pedicle_w, pedicle_h = 12, 15
        # Left pedicle
        draw.ellipse([center_x - vert_w//2 + 8, center_y - vert_h//2 - 8,
                     center_x - vert_w//2 + 8 + pedicle_w, center_y - vert_h//2 - 8 + pedicle_h], fill=200)
        # Right pedicle
        draw.ellipse([center_x + vert_w//2 - 8 - pedicle_w, center_y - vert_h//2 - 8,
                     center_x + vert_w//2 - 8, center_y - vert_h//2 - 8 + pedicle_h], fill=200)
        
        # Laminae
        lamina_w = 25
        # Left lamina
        draw.arc([center_x - lamina_w, center_y - vert_h//2 - 20,
                 center_x, center_y - vert_h//2 + 5], start=45, end=135, fill=200, width=4)
        # Right lamina
        draw.arc([center_x, center_y - vert_h//2 - 20,
                 center_x + lamina_w, center_y - vert_h//2 + 5], start=45, end=135, fill=200, width=4)
        
        # Spinous process
        spinous_w = 8
        draw.ellipse([center_x - spinous_w//2, center_y - vert_h//2 - 25,
                     center_x + spinous_w//2, center_y - vert_h//2 - 5], fill=190)
        
        # Spinal canal (CSF density ~0-20 HU, dark)
        draw.ellipse([center_x - canal_w//2, center_y - vert_h//2 - canal_h - 5,
                     center_x + canal_w//2, center_y - vert_h//2 - 5], fill=40, outline=60)
        
        # Spinal cord/nerve roots (soft tissue density ~40-60 HU)
        if body_part == 'LSPINE':
            # Cauda equina - nerve roots
            for i, offset in enumerate([-6, -2, 2, 6]):
                draw.ellipse([center_x + offset - 1, center_y - vert_h//2 - 18,
                             center_x + offset + 1, center_y - vert_h//2 - 12], fill=80)
        else:
            cord_w = 8 if body_part == 'CSPINE' else 10
            draw.ellipse([center_x - cord_w//2, center_y - vert_h//2 - 18,
                         center_x + cord_w//2, center_y - vert_h//2 - 12], fill=80)
        
        # Transverse processes
        draw.ellipse([center_x - vert_w//2 - transverse_size, center_y - 8,
                     center_x - vert_w//2, center_y + 8], fill=180)
        draw.ellipse([center_x + vert_w//2, center_y - 8,
                     center_x + vert_w//2 + transverse_size, center_y + 8], fill=180)
        
        # Add ribs for thoracic spine
        if body_part == 'TSPINE':
            rib_length = 60
            for side in [-1, 1]:
                rib_start_x = center_x + side * (vert_w//2 + 15)
                rib_end_x = center_x + side * (vert_w//2 + rib_length)
                draw.arc([rib_start_x - 10, center_y - 30,
                         rib_end_x + 10, center_y + 30], 
                        start=0 if side > 0 else 180, end=180 if side > 0 else 360, 
                        fill=190, width=3)
        
        # Intervertebral disc (if present on this slice)
        if slice_num % 5 == 0:  # Disc every 5th slice
            disc_w = vert_w - 8
            disc_h = 6 if body_part == 'CSPINE' else 10
            # Disc material (soft tissue density)
            draw.ellipse([center_x - disc_w//2, center_y + vert_h//2,
                         center_x + disc_w//2, center_y + vert_h//2 + disc_h], fill=90, outline=110)
        
        # Paravertebral soft tissue (muscle density ~40-60 HU)
        soft_w, soft_h = width//2.5, height//3
        draw.ellipse([center_x - soft_w, center_y - soft_h,
                     center_x + soft_w, center_y + soft_h], fill=70, outline=90)
        
        # Add some calcifications or artifacts occasionally
        if random.randint(0, 4) == 0:  # 20% chance
            calc_x = center_x + random.randint(-vert_w//2, vert_w//2)
            calc_y = center_y + random.randint(-vert_h//2, vert_h//2)
            draw.ellipse([calc_x - 2, calc_y - 2, calc_x + 2, calc_y + 2], fill=240)
    
    else:
        # Generic body cross-section
        body_w, body_h = width//3, height//3
        draw.ellipse([center_x - body_w, center_y - body_h,
                     center_x + body_w, center_y + body_h], fill=100, outline=130)
    
    # Add some noise for realism
    _add_medical_noise(image, 0.05)
    
    return image

def _generate_mr_image(image, draw, body_part: str, width: int, height: int, slice_num: int, total_slices: int):
    """Generate MR-like images with different tissue contrasts."""
    
    center_x, center_y = width // 2, height // 2
    
    if body_part in ['HEAD', 'BRAIN']:
        # Skull (dark in MR)
        skull_radius = min(width, height) // 3
        draw.ellipse([center_x - skull_radius, center_y - skull_radius, 
                     center_x + skull_radius, center_y + skull_radius], fill=80, outline=100)
        
        # Brain tissue (bright in T1)
        brain_radius = skull_radius - 15
        draw.ellipse([center_x - brain_radius, center_y - brain_radius,
                     center_x + brain_radius, center_y + brain_radius], fill=160, outline=180)
        
        # White matter (brighter)
        wm_radius = brain_radius - 30
        draw.ellipse([center_x - wm_radius, center_y - wm_radius,
                     center_x + wm_radius, center_y + wm_radius], fill=200)
        
        # CSF/ventricles (dark)
        csf_size = 25
        draw.ellipse([center_x - csf_size, center_y - csf_size//2,
                     center_x + csf_size, center_y + csf_size//2], fill=60)
        
    elif body_part in ['SPINE', 'LSPINE', 'CSPINE', 'TSPINE', 'SSPINE']:
        # Determine spinal region characteristics
        if body_part == 'CSPINE':
            # Cervical spine - smaller vertebrae, more curvature
            vert_w, vert_h = 35, 25
            cord_signal = 200  # Bright cord signal
            muscle_extent = width//4  # Less muscle mass
        elif body_part == 'TSPINE':
            # Thoracic spine - medium vertebrae, ribs visible
            vert_w, vert_h = 45, 30
            cord_signal = 190
            muscle_extent = width//3
            # Add rib elements for thoracic
            for rib_offset in [-80, 80]:
                draw.arc([center_x + rib_offset - 30, center_y - 40, 
                         center_x + rib_offset + 30, center_y + 40], 
                        start=0, end=180, fill=120, width=3)
        elif body_part == 'LSPINE':
            # Lumbar spine - larger vertebrae, prominent psoas muscles
            vert_w, vert_h = 55, 40
            cord_signal = 180  # Cauda equina region
            muscle_extent = width//2.5
            # Add psoas muscles
            draw.ellipse([center_x - 100, center_y - 20, center_x - 60, center_y + 60], fill=120)
            draw.ellipse([center_x + 60, center_y - 20, center_x + 100, center_y + 60], fill=120)
        else:
            # Generic spine
            vert_w, vert_h = 50, 35
            cord_signal = 190
            muscle_extent = width//3
        
        # Vertebral body (intermediate signal) - bone marrow bright on T1
        draw.ellipse([center_x - vert_w//2, center_y - vert_h//2,
                     center_x + vert_w//2, center_y + vert_h//2], fill=150, outline=170)
        
        # Posterior elements (laminae, spinous process)
        lamina_w, lamina_h = vert_w//3, vert_h//2
        # Left lamina
        draw.ellipse([center_x - vert_w//2 + 5, center_y - vert_h//2 - 15,
                     center_x - vert_w//2 + 5 + lamina_w, center_y - vert_h//2 - 15 + lamina_h], fill=140)
        # Right lamina  
        draw.ellipse([center_x + vert_w//2 - 5 - lamina_w, center_y - vert_h//2 - 15,
                     center_x + vert_w//2 - 5, center_y - vert_h//2 - 15 + lamina_h], fill=140)
        # Spinous process
        draw.ellipse([center_x - 8, center_y - vert_h//2 - 25,
                     center_x + 8, center_y - vert_h//2 - 5], fill=130)
        
        # Spinal cord/cauda equina (bright on T2, intermediate on T1)
        if body_part == 'LSPINE':
            # Cauda equina - multiple nerve roots
            for i, offset in enumerate([-8, -3, 2, 7]):
                nerve_signal = cord_signal - (i * 10)
                draw.ellipse([center_x + offset - 2, center_y - vert_h//2 - 20,
                             center_x + offset + 2, center_y - vert_h//2 - 10], fill=nerve_signal)
        else:
            # Spinal cord
            cord_w, cord_h = 12 if body_part == 'CSPINE' else 15, 18
            draw.ellipse([center_x - cord_w//2, center_y - vert_h//2 - cord_h - 5,
                         center_x + cord_w//2, center_y - vert_h//2 - 5], fill=cord_signal, outline=cord_signal + 20)
        
        # CSF around cord (very bright on T2, dark on T1) - simulate T2-weighted
        csf_w, csf_h = 28, 35
        draw.ellipse([center_x - csf_w//2, center_y - vert_h//2 - csf_h - 5,
                     center_x + csf_w//2, center_y - vert_h//2 - 5], fill=60, outline=80)
        
        # Intervertebral disc - varies by slice
        if slice_num % 4 == 0:  # Disc every 4th slice for more realistic spacing
            disc_w, disc_h = vert_w - 5, 8 if body_part == 'CSPINE' else 12
            # Nucleus pulposus (center, bright on T2)
            draw.ellipse([center_x - disc_w//2, center_y + vert_h//2,
                         center_x + disc_w//2, center_y + vert_h//2 + disc_h], fill=100, outline=120)
            # Annulus fibrosus (darker rim)
            draw.ellipse([center_x - disc_w//2 + 3, center_y + vert_h//2 + 2,
                         center_x + disc_w//2 - 3, center_y + vert_h//2 + disc_h - 2], fill=140)
        
        # Paravertebral muscles
        muscle_w, muscle_h = muscle_extent, height//3
        # Erector spinae muscles
        draw.ellipse([center_x - muscle_w - 20, center_y - muscle_h,
                     center_x - 40, center_y + muscle_h], fill=110, outline=130)
        draw.ellipse([center_x + 40, center_y - muscle_h,
                     center_x + muscle_w + 20, center_y + muscle_h], fill=110, outline=130)
        
        # Ligamentum flavum (small bright structure)
        if random.randint(0, 2) == 0:  # Not visible on every slice
            draw.line([center_x - 15, center_y - vert_h//2 - 5, 
                      center_x + 15, center_y - vert_h//2 - 5], fill=180, width=2)
    
    else:
        # Generic MR appearance
        body_w, body_h = width//3, height//3
        draw.ellipse([center_x - body_w, center_y - body_h,
                     center_x + body_w, center_y + body_h], fill=130, outline=150)
    
    # MR has less noise but more artifacts
    _add_medical_noise(image, 0.02)
    
    return image

def _generate_xray_image(image, draw, body_part: str, width: int, height: int):
    """Generate X-ray like projection images."""
    
    center_x, center_y = width // 2, height // 2
    
    if body_part in ['CHEST', 'LUNG']:
        # Chest outline (ribs)
        for i in range(8):  # Draw ribs
            rib_y = center_y - 100 + i * 25
            # Left ribs
            draw.arc([center_x - 150, rib_y - 30, center_x - 20, rib_y + 30], 
                    start=0, end=180, fill=180, width=3)
            # Right ribs
            draw.arc([center_x + 20, rib_y - 30, center_x + 150, rib_y + 30], 
                    start=0, end=180, fill=180, width=3)
        
        # Spine (bright vertical line)
        draw.rectangle([center_x - 8, center_y - 150, center_x + 8, center_y + 150], fill=200)
        
        # Heart shadow
        heart_w, heart_h = 80, 100
        draw.ellipse([center_x - heart_w//2 - 20, center_y - heart_h//2,
                     center_x + heart_w//2 - 20, center_y + heart_h//2], fill=140, outline=160)
        
        # Diaphragm
        draw.arc([center_x - 120, center_y + 80, center_x + 120, center_y + 180], 
                start=0, end=180, fill=160, width=5)
        
    elif body_part in ['SPINE', 'LSPINE', 'CSPINE', 'TSPINE', 'SSPINE']:
        # X-ray spine (AP or lateral projection)
        view_type = random.choice(['AP', 'LAT'])  # Anterior-Posterior or Lateral
        
        if view_type == 'AP':
            # AP (front-to-back) view
            if body_part == 'CSPINE':
                # Cervical spine AP - smaller vertebrae, visible through skull base
                vertebrae_count = 7
                vert_start_y = center_y - 120
                vert_spacing = 20
                vert_width = 25
            elif body_part == 'TSPINE':
                # Thoracic spine AP - ribs visible
                vertebrae_count = 12
                vert_start_y = center_y - 150
                vert_spacing = 25
                vert_width = 30
                # Draw ribs
                for i in range(12):
                    rib_y = vert_start_y + i * vert_spacing
                    # Left ribs
                    draw.arc([center_x - 100, rib_y - 20, center_x - 10, rib_y + 20], 
                            start=0, end=180, fill=160, width=2)
                    # Right ribs
                    draw.arc([center_x + 10, rib_y - 20, center_x + 100, rib_y + 20], 
                            start=0, end=180, fill=160, width=2)
            elif body_part == 'LSPINE':
                # Lumbar spine AP - larger vertebrae
                vertebrae_count = 5
                vert_start_y = center_y - 80
                vert_spacing = 32
                vert_width = 35
                # Add iliac crests
                draw.arc([center_x - 60, center_y + 60, center_x + 60, center_y + 120], 
                        start=0, end=180, fill=170, width=4)
            else:
                # Generic spine
                vertebrae_count = 5
                vert_start_y = center_y - 80
                vert_spacing = 30
                vert_width = 30
            
            # Draw vertebral bodies and pedicles (AP view)
            for i in range(vertebrae_count):
                vert_y = vert_start_y + i * vert_spacing
                # Vertebral body (rectangular in AP view)
                draw.rectangle([center_x - vert_width//2, vert_y - 12, 
                               center_x + vert_width//2, vert_y + 12], fill=180, outline=200, width=1)
                # Pedicles (appear as circles on AP view)
                pedicle_offset = vert_width//2 + 8
                draw.ellipse([center_x - pedicle_offset - 6, vert_y - 6, 
                             center_x - pedicle_offset + 6, vert_y + 6], fill=160)
                draw.ellipse([center_x + pedicle_offset - 6, vert_y - 6, 
                             center_x + pedicle_offset + 6, vert_y + 6], fill=160)
                # Spinous process (central line)
                draw.line([center_x, vert_y - 8, center_x, vert_y + 8], fill=140, width=2)
                
        else:
            # Lateral view
            if body_part == 'CSPINE':
                vertebrae_count = 7
                vert_start_y = center_y - 120
                vert_spacing = 18
                vert_width = 25
                vert_height = 15
                # Add skull base
                draw.ellipse([center_x - 40, center_y - 150, center_x + 20, center_y - 120], 
                           fill=150, outline=170, width=2)
            elif body_part == 'LSPINE':
                vertebrae_count = 5
                vert_start_y = center_y - 70
                vert_spacing = 28
                vert_width = 35
                vert_height = 22
                # Add sacrum
                draw.polygon([(center_x - 15, center_y + 70), (center_x + 15, center_y + 70), 
                             (center_x + 10, center_y + 110), (center_x - 10, center_y + 110)], 
                            fill=170, outline=190)
            else:
                vertebrae_count = 5
                vert_start_y = center_y - 70
                vert_spacing = 25
                vert_width = 30
                vert_height = 18
            
            # Draw vertebral bodies (lateral view - rectangular)
            for i in range(vertebrae_count):
                vert_y = vert_start_y + i * vert_spacing
                # Vertebral body
                draw.rectangle([center_x - vert_width//2, vert_y - vert_height//2, 
                               center_x + vert_width//2, vert_y + vert_height//2], 
                              fill=180, outline=200, width=1)
                # Posterior elements
                draw.rectangle([center_x + vert_width//2 - 5, vert_y - vert_height//2 - 8, 
                               center_x + vert_width//2 + 15, vert_y + vert_height//2 + 8], 
                              fill=160, outline=180)
                # Intervertebral disc space
                if i < vertebrae_count - 1:
                    disc_y = vert_y + vert_spacing//2
                    draw.line([center_x - vert_width//2 + 3, disc_y, 
                              center_x + vert_width//2 - 3, disc_y], fill=120, width=2)
        
        # Add soft tissue shadows
        soft_tissue_w = width//4
        draw.ellipse([center_x - soft_tissue_w - 50, center_y - 100, 
                     center_x - 50, center_y + 100], fill=90, outline=110)
        draw.ellipse([center_x + 50, center_y - 100, 
                     center_x + soft_tissue_w + 50, center_y + 100], fill=90, outline=110)
        
    elif body_part in ['HEAD', 'SKULL']:
        # Skull outline
        skull_w, skull_h = width//3, height//3
        draw.ellipse([center_x - skull_w, center_y - skull_h,
                     center_x + skull_w, center_y + skull_h], fill=160, outline=180, width=8)
        
        # Sinus cavities (dark)
        draw.ellipse([center_x - 30, center_y - skull_h + 20,
                     center_x + 30, center_y - skull_h + 60], fill=80)
        
    else:
        # Generic bone structure
        draw.ellipse([center_x - 60, center_y - 80, center_x + 60, center_y + 80], fill=150, outline=180, width=4)
    
    # X-rays have more scattered radiation
    _add_medical_noise(image, 0.08)
    
    return image

def _generate_ultrasound_image(image, draw, body_part: str, width: int, height: int):
    """Generate ultrasound-like images with characteristic speckle."""
    
    # Ultrasound sector shape (fan beam)
    center_x = width // 2
    top_y = 50
    
    # Draw sector outline
    for angle in range(-60, 61, 5):  # 120 degree sector
        end_x = int(center_x + (height - top_y) * np.sin(np.radians(angle)))
        end_y = height - 20
        draw.line([(center_x, top_y), (end_x, end_y)], fill=100, width=1)
    
    # Add some organ-like structures
    if body_part in ['ABDOMEN', 'LIVER']:
        # Liver edge
        draw.arc([center_x - 80, top_y + 50, center_x + 80, top_y + 150], 
                start=0, end=180, fill=140, width=3)
        # Portal vein
        draw.ellipse([center_x - 40, top_y + 80, center_x + 40, top_y + 100], fill=80)
        
    elif body_part in ['HEART']:
        # Heart chambers
        draw.ellipse([center_x - 60, top_y + 80, center_x + 20, top_y + 160], fill=120)  # LV
        draw.ellipse([center_x - 20, top_y + 70, center_x + 40, top_y + 130], fill=110)  # RV
    
    # Add ultrasound speckle pattern
    _add_ultrasound_speckle(image, width, height)
    
    return image

def _generate_nuclear_image(image, draw, body_part: str, width: int, height: int):
    """Generate nuclear medicine/PET-like images with uptake patterns."""
    
    center_x, center_y = width // 2, height // 2
    
    # Body outline (faint)
    body_w, body_h = width//3, height//2
    draw.ellipse([center_x - body_w, center_y - body_h,
                 center_x + body_w, center_y + body_h], fill=60, outline=80)
    
    # Hot spots (high uptake areas)
    if body_part in ['CHEST']:
        # Heart uptake
        draw.ellipse([center_x - 30, center_y - 20, center_x + 30, center_y + 40], fill=200)
        # Liver uptake
        draw.ellipse([center_x + 20, center_y + 10, center_x + 80, center_y + 60], fill=160)
        
    elif body_part == 'HEAD':
        # Brain uptake
        brain_radius = 80
        draw.ellipse([center_x - brain_radius, center_y - brain_radius,
                     center_x + brain_radius, center_y + brain_radius], fill=180)
        
    # Add physiological uptake patterns
    for _ in range(random.randint(3, 8)):
        x = random.randint(50, width - 50)
        y = random.randint(50, height - 50)
        size = random.randint(10, 30)
        intensity = random.randint(120, 200)
        draw.ellipse([x - size, y - size, x + size, y + size], fill=intensity)
    
    # Nuclear images are typically smoothed
    _add_medical_noise(image, 0.15)
    
    return image

def _generate_mammogram_image(image, draw, width: int, height: int):
    """Generate mammography-like images."""
    
    # Breast tissue outline
    breast_w, breast_h = width//2, height - 100
    draw.ellipse([50, 50, 50 + breast_w, 50 + breast_h], fill=120, outline=140)
    
    # Fibroglandular tissue (brighter)
    for _ in range(8):
        x = random.randint(70, 70 + breast_w - 60)
        y = random.randint(70, 70 + breast_h - 60)
        w = random.randint(20, 60)
        h = random.randint(15, 40)
        draw.ellipse([x, y, x + w, y + h], fill=160)
    
    # Pectoral muscle (if MLO view)
    draw.polygon([(0, 0), (150, 0), (50, 200)], fill=140)
    
    # High contrast for mammography
    _add_medical_noise(image, 0.03)
    
    return image

def _add_medical_noise(image, noise_level: float):
    """Add realistic medical imaging noise."""
    pixels = image.load()
    width, height = image.size
    
    for x in range(width):
        for y in range(height):
            if random.random() < noise_level:
                current = pixels[x, y]
                noise = random.randint(-20, 20)
                new_val = max(0, min(255, current + noise))
                pixels[x, y] = new_val

def _add_ultrasound_speckle(image, width: int, height: int):
    """Add characteristic ultrasound speckle pattern."""
    pixels = image.load()
    
    for x in range(width):
        for y in range(height):
            if random.random() < 0.3:  # 30% chance of speckle
                speckle = random.randint(80, 180)
                pixels[x, y] = speckle

def _get_technical_parameters(modality: str, slice_num: int) -> list:
    """Return modality-specific technical parameters for display."""
    
    if modality == 'CT':
        return [
            f"kVp: {random.choice([120, 140])}",
            f"mAs: {random.randint(200, 400)}",
            f"Slice: {slice_num}mm",
            f"WW: {random.randint(350, 450)}",
            f"WL: {random.randint(35, 45)}"
        ]
    elif modality == 'MR':
        return [
            f"TR: {random.randint(400, 600)}ms",
            f"TE: {random.randint(8, 15)}ms",
            f"Slice: {slice_num}mm",
            f"NEX: {random.choice([1, 2, 4])}",
            f"FOV: {random.randint(22, 28)}cm"
        ]
    elif modality in ['DX', 'CR']:
        return [
            f"kVp: {random.choice([80, 90, 100, 110])}",
            f"mAs: {random.randint(5, 25)}",
            f"Grid: {random.choice(['8:1', '10:1', '12:1'])}",
            f"SID: {random.choice([100, 150, 180])}cm"
        ]
    elif modality == 'US':
        return [
            f"Freq: {random.choice([2.5, 3.5, 5.0])}MHz",
            f"Depth: {random.randint(15, 25)}cm",
            f"Gain: {random.randint(45, 65)}%",
            f"Power: {random.randint(80, 100)}%"
        ]
    else:
        return []

def _generate_sr_report_text(modality: str, study_description: str, body_part: str) -> str:
    """Generate realistic report text based on modality and study information."""
    fake = Faker()
    
    # Common report elements
    indication = f"Clinical indication: {fake.sentence()}"
    technique = ""
    findings = ""
    impression = ""
    
    if modality in ['CT']:
        technique = f"Technique: Axial CT images of the {body_part.lower()} were obtained without contrast enhancement."
        if 'CHEST' in study_description.upper():
            findings = "Findings: The lungs are clear without evidence of consolidation, pleural effusion, or pneumothorax. The heart size is within normal limits. No mediastinal lymphadenopathy is identified. The osseous structures appear intact."
            impression = "Impression: Normal chest CT examination."
        elif 'ABDOMEN' in study_description.upper() or 'PELVIS' in study_description.upper():
            findings = "Findings: The liver, spleen, pancreas, and kidneys appear normal in size and attenuation. No intra-abdominal lymphadenopathy or free fluid is identified. The bowel loops appear unremarkable."
            impression = "Impression: Normal abdominal CT examination."
        elif 'HEAD' in study_description.upper() or 'BRAIN' in study_description.upper():
            findings = "Findings: No acute intracranial abnormality is identified. The ventricles are normal in size and configuration. No mass effect or midline shift is present."
            impression = "Impression: Normal head CT examination."
        else:
            findings = f"Findings: The {body_part.lower()} structures appear within normal limits. No acute abnormality is identified."
            impression = f"Impression: Normal {modality} examination of the {body_part.lower()}."
    
    elif modality in ['MR']:
        technique = f"Technique: Multiplanar MR images of the {body_part.lower()} were obtained using standard sequences."
        if 'BRAIN' in study_description.upper() or 'HEAD' in study_description.upper():
            findings = "Findings: Normal brain parenchyma without evidence of acute infarct, hemorrhage, or mass lesion. The ventricular system is normal in size. No abnormal enhancement is identified."
            impression = "Impression: Normal brain MRI examination."
        elif 'SPINE' in study_description.upper():
            findings = "Findings: Normal vertebral body height and alignment. The intervertebral discs show normal signal intensity. The spinal cord appears normal. No significant stenosis is identified."
            impression = "Impression: Normal spine MRI examination."
        elif 'KNEE' in study_description.upper():
            findings = "Findings: The menisci appear intact. The cruciate and collateral ligaments are normal. No joint effusion is identified. The articular cartilage appears preserved."
            impression = "Impression: Normal knee MRI examination."
        else:
            findings = f"Findings: The {body_part.lower()} structures demonstrate normal signal characteristics. No abnormal enhancement or mass lesion is identified."
            impression = f"Impression: Normal {modality} examination of the {body_part.lower()}."
    
    elif modality in ['DX', 'CR']:
        technique = f"Technique: {modality} images of the {body_part.lower()} were obtained."
        if 'CHEST' in study_description.upper():
            findings = "Findings: The heart size is within normal limits. The lungs are clear without consolidation or pleural effusion. The mediastinal contours are normal. No acute osseous abnormality is identified."
            impression = "Impression: Normal chest radiograph."
        elif 'ABDOMEN' in study_description.upper():
            findings = "Findings: Normal bowel gas pattern. No evidence of obstruction or free air. The osseous structures appear intact."
            impression = "Impression: Normal abdominal radiograph."
        else:
            findings = f"Findings: The {body_part.lower()} structures appear within normal limits. No acute abnormality is identified."
            impression = f"Impression: Normal {modality} examination of the {body_part.lower()}."
    
    elif modality in ['US']:
        technique = f"Technique: Real-time ultrasound examination of the {body_part.lower()} was performed."
        if 'ABDOMEN' in study_description.upper():
            findings = "Findings: The liver demonstrates normal size and echogenicity. The gallbladder appears normal without stones or wall thickening. The kidneys are normal in size and echogenicity. No free fluid is identified."
            impression = "Impression: Normal abdominal ultrasound examination."
        elif 'PELVIS' in study_description.upper():
            findings = "Findings: The uterus and ovaries appear normal in size and echogenicity. No adnexal masses or free fluid is identified."
            impression = "Impression: Normal pelvic ultrasound examination."
        else:
            findings = f"Findings: The {body_part.lower()} structures demonstrate normal echogenicity and vascularity. No abnormal masses or fluid collections are identified."
            impression = f"Impression: Normal ultrasound examination of the {body_part.lower()}."
    
    elif modality in ['NM']:
        technique = f"Technique: Nuclear medicine imaging of the {body_part.lower()} was performed following intravenous administration of appropriate radiopharmaceutical."
        if 'BONE' in study_description.upper():
            findings = "Findings: Normal symmetric uptake is seen throughout the osseous structures. No areas of abnormal increased or decreased uptake are identified."
            impression = "Impression: Normal bone scan."
        else:
            findings = "Findings: Normal biodistribution of the radiopharmaceutical. No areas of abnormal uptake are identified."
            impression = "Impression: Normal nuclear medicine examination."
    
    elif modality in ['MG']:
        technique = "Technique: Digital mammography was performed with standard CC and MLO views bilaterally."
        findings = "Findings: The breast tissue demonstrates scattered fibroglandular density (BI-RADS 2). No suspicious masses, calcifications, or architectural distortions are identified."
        impression = "Impression: BI-RADS 1 - Negative mammogram."
    
    else:
        # Generic report for other modalities
        technique = f"Technique: {modality} examination of the {body_part.lower()} was performed."
        findings = f"Findings: The {body_part.lower()} structures appear within normal limits for this examination."
        impression = f"Impression: Normal {modality} examination."
    
    # Combine all sections
    report_sections = [
        indication,
        "",
        technique,
        "",
        findings,
        "",
        impression,
        "",
        f"Electronically signed by: Dr. {fake.last_name()}, {fake.last_name()} Radiology",
        f"Date/Time: {datetime.datetime.now().strftime('%m/%d/%Y %H:%M:%S')}"
    ]
    
    return "\n".join(report_sections)

def _create_sr_object(study_instance_uid: str, series_instance_uid: str, patient_name: str, 
                     patient_id: str, study_date: str, study_time: str, accession_number: str,
                     modality: str, study_description: str, body_part: str, 
                     patient_birth_date: str = '19800101', patient_sex: str = 'O') -> Dataset:
    """Create a DICOM SR (Structured Report) object with generated report text."""
    
    # Generate report text
    report_text = _generate_sr_report_text(modality, study_description, body_part)
    
    # Create SR dataset
    file_meta = FileMetaDataset()
    file_meta.MediaStorageSOPClassUID = UID("1.2.840.10008.5.1.4.1.1.88.11")  # Basic Text SR Storage
    file_meta.MediaStorageSOPInstanceUID = generate_uid()
    file_meta.TransferSyntaxUID = ImplicitVRLittleEndian
    file_meta.ImplementationClassUID = PYDICOM_IMPLEMENTATION_UID
    file_meta.ImplementationVersionName = "PYDICOM " + pydicom.__version__
    file_meta.FileMetaInformationVersion = b'\x00\x01'

    # Main Dataset
    ds = Dataset()
    ds.file_meta = file_meta
    # Transfer syntax is set in file_meta, no need to set deprecated attributes

    # Patient Information
    ds.PatientName = patient_name
    ds.PatientID = patient_id
    ds.PatientBirthDate = patient_birth_date
    ds.PatientSex = patient_sex

    # Study Information
    ds.AccessionNumber = accession_number
    ds.StudyInstanceUID = study_instance_uid
    ds.StudyDate = study_date
    ds.StudyTime = study_time
    ds.StudyID = "1"
    ds.StudyDescription = study_description
    ds.ReferringPhysicianName = "SIMULATION^DOCTOR"

    # Series Information for SR
    ds.SeriesInstanceUID = series_instance_uid
    ds.SeriesNumber = "999"  # Use high number to distinguish from imaging series
    ds.Modality = "SR"  # Structured Report
    ds.SeriesDescription = f"SR Report for {study_description}"

    # Instance Information
    ds.SOPClassUID = UID("1.2.840.10008.5.1.4.1.1.88.11")  # Basic Text SR Storage
    ds.SOPInstanceUID = file_meta.MediaStorageSOPInstanceUID
    ds.InstanceNumber = 1
    ds.ContentDate = study_date
    ds.ContentTime = study_time

    # Equipment Information
    ds.Manufacturer = "DICOM Generator"
    ds.ManufacturerModelName = "Python-SR-Generator-v1.0"
    ds.InstitutionName = "Gen Hospital"

    # SR Specific Attributes
    ds.ValueType = "CONTAINER"
    ds.ConceptNameCodeSequence = [Dataset()]
    ds.ConceptNameCodeSequence[0].CodeValue = "18782-3"
    ds.ConceptNameCodeSequence[0].CodingSchemeDesignator = "LN"
    ds.ConceptNameCodeSequence[0].CodeMeaning = "Radiology Report"

    ds.ContinuityOfContent = "SEPARATE"
    ds.CompletionFlag = "COMPLETE"
    ds.VerificationFlag = "VERIFIED"

    # Content Sequence - Main report content
    ds.ContentSequence = [Dataset()]
    content_item = ds.ContentSequence[0]
    content_item.RelationshipType = "CONTAINS"
    content_item.ValueType = "TEXT"
    
    content_item.ConceptNameCodeSequence = [Dataset()]
    content_item.ConceptNameCodeSequence[0].CodeValue = "121060"
    content_item.ConceptNameCodeSequence[0].CodingSchemeDesignator = "DCM"
    content_item.ConceptNameCodeSequence[0].CodeMeaning = "History"

    content_item.TextValue = report_text

    # Additional SR metadata
    ds.PerformingPhysicianName = f"SIMULATION^RADIOLOGIST^{Faker().last_name()}"
    ds.ContentCreatorName = ds.PerformingPhysicianName

    return ds

def create_study_files(output_dir: str, num_images: int, overrides: dict, generate_pixels: bool = True, burn_patient_info: bool = False, generate_report: bool = False):
    logging.info(f"DICOM Generator: Starting study generation in {output_dir}")
    
    fake = Faker()
    
    # --- Study-Level Data ---
    study_instance_uid = overrides.get('StudyInstanceUID', generate_uid())
    patient_name = overrides.get('PatientName', fake.name().replace(" ", "^"))
    patient_id = overrides.get('PatientID', '12345678')
    accession_number = overrides.get('AccessionNumber', 'ACC12345678')
    study_date = overrides.get('StudyDate', datetime.date.today().strftime("%Y%m%d"))
    study_time = overrides.get('StudyTime', datetime.datetime.now().strftime("%H%M%S.%f"))
    chosen_modality = overrides.get('Modality', 'CT')
    study_description = overrides.get('StudyDescription', f"Generated {chosen_modality} Study")
    body_part_examined = overrides.get('BodyPartExamined', _infer_body_part_from_description(study_description))

    # Map modality to appropriate SOP Class UID
    sop_class_mapping = {
        'CT': "1.2.840.10008.5.1.4.1.1.2",      # CT Image Storage
        'MR': "1.2.840.10008.5.1.4.1.1.4",      # MR Image Storage
        'DX': "1.2.840.10008.5.1.4.1.1.1.1",    # Digital X-Ray Image Storage - For Presentation
        'CR': "1.2.840.10008.5.1.4.1.1.1",      # Computed Radiography Image Storage
        'US': "1.2.840.10008.5.1.4.1.1.6.1",    # Ultrasound Image Storage
        'NM': "1.2.840.10008.5.1.4.1.1.20",     # Nuclear Medicine Image Storage
        'XA': "1.2.840.10008.5.1.4.1.1.12.1",   # X-Ray Angiographic Image Storage
        'RF': "1.2.840.10008.5.1.4.1.1.12.2",   # X-Ray Radiofluoroscopic Image Storage
        'MG': "1.2.840.10008.5.1.4.1.1.1.2",    # Digital Mammography X-Ray Image Storage - For Presentation
        'PT': "1.2.840.10008.5.1.4.1.1.128",    # Positron Emission Tomography Image Storage
    }
    
    sop_class_uid = sop_class_mapping.get(chosen_modality, "1.2.840.10008.5.1.4.1.1.2")  # Default to CT
    logging.info(f"DICOM Generator: Using modality '{chosen_modality}' with SOP Class UID '{sop_class_uid}'")

    study_output_path = Path(output_dir)
    study_output_path.mkdir(parents=True, exist_ok=True)
    
    series_instance_uid = generate_uid()
    frame_of_reference_uid = generate_uid() # Single FOR for the whole series
    generated_files = []

    for i in range(num_images):
        instance_num = i + 1
        
        # --- Instance-Level Data ---
        sop_instance_uid = generate_uid()
        
        # --- File Meta Information ---
        file_meta = FileMetaDataset()
        file_meta.MediaStorageSOPClassUID = UID(sop_class_uid)
        file_meta.MediaStorageSOPInstanceUID = sop_instance_uid
        file_meta.TransferSyntaxUID = ImplicitVRLittleEndian
        file_meta.ImplementationClassUID = PYDICOM_IMPLEMENTATION_UID
        file_meta.ImplementationVersionName = "PYDICOM " + pydicom.__version__
        file_meta.FileMetaInformationVersion = b'\x00\x01'

        # --- Main Dataset ---
        ds = Dataset()
        ds.file_meta = file_meta
        # Transfer syntax is set in file_meta, no need to set deprecated attributes

        # --- Patient and Study Information ---
        ds.PatientName = patient_name
        ds.PatientID = patient_id
        ds.PatientBirthDate = overrides.get('PatientBirthDate', '19800101')
        ds.PatientSex = overrides.get('PatientSex', 'O')
        
        ds.AccessionNumber = accession_number
        ds.StudyInstanceUID = study_instance_uid
        ds.StudyDate = study_date
        ds.StudyTime = study_time
        ds.StudyID = "1"
        ds.StudyDescription = study_description
        ds.ReferringPhysicianName = "SIMULATION^DOCTOR"
        
        # --- Series Information ---
        ds.SeriesInstanceUID = series_instance_uid
        ds.SeriesNumber = "1"
        ds.Modality = chosen_modality
        ds.BodyPartExamined = body_part_examined
        ds.SeriesDescription = f"{chosen_modality} {body_part_examined}"
        
        # --- Instance Information ---
        ds.SOPClassUID = sop_class_uid
        ds.SOPInstanceUID = sop_instance_uid
        ds.InstanceNumber = instance_num
        ds.ContentDate = study_date
        ds.ContentTime = study_time
        
        # --- Equipment Information ---
        ds.Manufacturer = "DICOM Generator"
        ds.ManufacturerModelName = "Python-Generator-v3.0"
        ds.InstitutionName = "Gen Hospital"

        # --- Image Type and Positional Information ---
        slice_thickness = 5.0
        pixel_spacing = [1.0, 1.0]

        if chosen_modality in ['CT', 'MR']:
            ds.ImageType = ["ORIGINAL", "PRIMARY", "AXIAL"]
            ds.ImagePositionPatient = [0.0, 0.0, float((instance_num -1) * slice_thickness)]
            ds.ImageOrientationPatient = [1.0, 0.0, 0.0, 0.0, 1.0, 0.0]
            ds.FrameOfReferenceUID = frame_of_reference_uid
            ds.SliceLocation = float((instance_num - 1) * slice_thickness)
            ds.SliceThickness = slice_thickness
            ds.PixelSpacing = pixel_spacing
            ds.PatientPosition = "HFS"
        elif chosen_modality in ['DX', 'CR', 'MG']:
            ds.ImageType = ["ORIGINAL", "PRIMARY"]
            ds.PatientOrientation = ["A", "P"] 
            ds.ViewPosition = "AP"
        else:
            ds.ImageType = ["ORIGINAL", "PRIMARY"]
            ds.PatientPosition = "HFS"

        # Apply any custom overrides from the user
        for key, value in overrides.items():
            setattr(ds, key, value)
            
        if generate_pixels:
            pixel_array = _generate_medical_image(
                chosen_modality, body_part_examined, 
                width=512, height=512, 
                slice_num=instance_num, total_slices=num_images
            )
            
            # --- Set Core Pixel Attributes ---
            ds.SamplesPerPixel = 1
            ds.PhotometricInterpretation = "MONOCHROME2"
            ds.NumberOfFrames = 1
            ds.Rows = pixel_array.shape[0]
            ds.Columns = pixel_array.shape[1]
            ds.PixelRepresentation = 0  # 0 for unsigned integers
            ds.BitsAllocated = 16
            # Planar configuration is required for multi-sample pixels, but good practice to include
            ds.PlanarConfiguration = 0 

            # --- Modality-Specific Pixel Handling ---
            if chosen_modality in ['DX', 'CR', 'MG']:
                ds.BitsStored = 14
                ds.HighBit = 13
            elif chosen_modality == 'CT':
                ds.BitsStored = 12
                ds.HighBit = 11
                ds.RescaleIntercept = -1024.0
                ds.RescaleSlope = 1.0
                ds.RescaleType = "HU"
            elif chosen_modality == 'MR':
                ds.BitsStored = 12
                ds.HighBit = 11
                ds.RescaleIntercept = 0.0
                ds.RescaleSlope = 1.0
            elif chosen_modality == 'US':
                ds.BitsStored = 16
                ds.HighBit = 15
            else: # Default case
                ds.BitsStored = 12
                ds.HighBit = 11

            # --- Dynamic Windowing ---
            pixel_mean = np.mean(pixel_array)
            pixel_std = np.std(pixel_array)
            window_center = pixel_mean
            window_width = pixel_std * 4
            
            if chosen_modality == 'CT':
                ds.WindowCenter = [40, window_center]
                ds.WindowWidth = [400, window_width]
                ds.WindowCenterWidthExplanation = ["SOFT_TISSUE", "AUTO"]
            else:
                ds.WindowCenter = window_center
                ds.WindowWidth = window_width

            # --- Add text overlays using PIL if available ---
            if HAS_PILLOW:
                max_val = (2**ds.BitsStored) - 1
                scaled_array = (pixel_array / max_val * 255.0).astype(np.uint8)
                pil_image = Image.fromarray(scaled_array, mode='L')  # type: ignore
                draw = ImageDraw.Draw(pil_image)  # type: ignore
                
                try:
                    font = ImageFont.truetype("DejaVuSans.ttf", 20)  # type: ignore
                    small_font = ImageFont.truetype("DejaVuSans.ttf", 14)  # type: ignore
                except IOError:
                    font = ImageFont.load_default()  # type: ignore
                    small_font = ImageFont.load_default()  # type: ignore

                # Only burn patient information if requested
                if burn_patient_info:
                    draw.text((10, 10), str(ds.PatientName).replace("^", " "), font=font, fill=255)
                    draw.text((10, 35), f"MRN: {ds.PatientID}", font=small_font, fill=255)
                
                draw.text((10, 512 - 40), f"Img: {ds.InstanceNumber}/{num_images}", font=small_font, fill=255)
                
                overlay_array_8bit = np.array(pil_image)
                pixel_array = (overlay_array_8bit / 255.0 * max_val).astype(np.uint16)

            # --- Set the Pixel Data (Corrected Method) ---
            # Assign the numpy array as bytes. pydicom requires PixelData to be bytes.
            ds.set_pixel_data(
                pixel_array,
                photometric_interpretation=ds.PhotometricInterpretation,
                bits_stored=ds.BitsStored
            )

        else:
            # Add required pixel attributes even if no pixel data is generated
            ds.SamplesPerPixel = 1
            ds.PhotometricInterpretation = "MONOCHROME2"
            ds.Rows = 512
            ds.Columns = 512
            ds.BitsAllocated = 16
            ds.BitsStored = 12
            ds.HighBit = 11
            ds.PixelRepresentation = 0
            ds.PixelData = b''
            
        # --- Save the DICOM file ---
        filepath = study_output_path / f"{chosen_modality}.{ds.SOPInstanceUID}.dcm"
        
        try:
            # pydicom.config.enforce_valid_values = True # Can be uncommented for strict validation
            ds.save_as(filepath, enforce_file_format=True)
            logging.info(f"Successfully saved PACS-compatible DICOM: {filepath} ({filepath.stat().st_size} bytes)")
            
        except Exception as e:
            logging.error(f"Critical error saving DICOM file '{filepath}': {e}")
            raise 
            
        generated_files.append(str(filepath.resolve()))

    # --- Generate SR (Structured Report) if requested ---
    if generate_report:
        logging.info("DICOM Generator: Creating SR object for study")
        sr_series_uid = generate_uid()
        
        try:
            sr_ds = _create_sr_object(
                study_instance_uid=study_instance_uid,
                series_instance_uid=sr_series_uid,
                patient_name=patient_name,
                patient_id=patient_id,
                study_date=study_date,
                study_time=study_time,
                accession_number=accession_number,
                modality=chosen_modality,
                study_description=study_description,
                body_part=body_part_examined,
                patient_birth_date=overrides.get('PatientBirthDate', '19800101'),
                patient_sex=overrides.get('PatientSex', 'O')
            )
            
            # Save SR file
            sr_filepath = study_output_path / f"SR.{sr_ds.SOPInstanceUID}.dcm"
            sr_ds.save_as(sr_filepath, enforce_file_format=True)
            logging.info(f"Successfully saved SR report: {sr_filepath} ({sr_filepath.stat().st_size} bytes)")
            generated_files.append(str(sr_filepath.resolve()))
            
        except Exception as e:
            logging.error(f"Error creating SR object: {e}")
            # Don't fail the entire generation if SR creation fails

    logging.info(f"DICOM Generator: Finished. Generated {len(generated_files)} files.")
    return generated_files