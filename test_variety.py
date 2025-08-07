#!/usr/bin/env python3

import random

# Simulate the enhanced modality selection
def test_modality_variety():
    print("Testing enhanced modality variety system...")
    
    # Same logic as in the updated simulation runner
    modality_weights = [
        ('DX', 35),    # Digital Radiography - most common
        ('CT', 25),    # CT scans - very common  
        ('MR', 20),    # MRI - common for soft tissue
        ('US', 10),    # Ultrasound - common and portable
        ('CR', 5),     # Computed Radiography - older but still used
        ('NM', 3),     # Nuclear Medicine - specialized
        ('MG', 2),     # Mammography - specialized
    ]
    
    # Create weighted list
    weighted_modalities = []
    for modality, weight in modality_weights:
        weighted_modalities.extend([modality] * weight)
    
    # Test with different run_id and patient combinations
    results = {}
    for run_id in range(1, 4):  # 3 different runs
        results[run_id] = []
        for patient_iter in range(1, 6):  # 5 patients per run
            # Use same seeding logic as the simulation runner
            random.seed(run_id * 1000 + patient_iter)
            modality = random.choice(weighted_modalities)
            results[run_id].append(modality)
    
    # Show results
    for run_id, modalities in results.items():
        print(f"Run {run_id}: {modalities}")
    
    # Count frequency across all runs
    all_modalities = []
    for modalities in results.values():
        all_modalities.extend(modalities)
    
    frequency = {}
    for modality in all_modalities:
        frequency[modality] = frequency.get(modality, 0) + 1
    
    print(f"\nOverall frequency across {len(all_modalities)} selections:")
    for modality, count in sorted(frequency.items(), key=lambda x: x[1], reverse=True):
        percentage = (count / len(all_modalities)) * 100
        print(f"  {modality}: {count} ({percentage:.1f}%)")
    
    print(f"\nExpected vs Actual distribution:")
    total_weight = sum(weight for _, weight in modality_weights)
    for modality, expected_weight in modality_weights:
        expected_pct = (expected_weight / total_weight) * 100
        actual_count = frequency.get(modality, 0)
        actual_pct = (actual_count / len(all_modalities)) * 100
        print(f"  {modality}: Expected {expected_pct:.1f}%, Got {actual_pct:.1f}%")

if __name__ == "__main__":
    test_modality_variety()
