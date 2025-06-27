# Air Quality Scoring System

## 1. Overview

This comprehensive air quality scoring system is designed for your Smart Cleaning Management Solution, aligned with the WELL Building Standard thresholds and other recognized health standards. Tailored for use with AM300 and GS301 sensor series, it translates environmental parameters into actionable scores to guide cleaning and ventilation decisions across various space types in your facility.

## 2. Scoring Methodology

The air quality score uses a 0-100 scale:

- **90-100**: Excellent air quality (No action needed)
- **80-89**: Good air quality (Routine maintenance)
- **60-79**: Moderate air quality (Monitor closely)
- **40-59**: Poor air quality (Requires attention)
- **Below 40**: Very poor air quality (Requires immediate action)

The overall score is a weighted average of individual parameter scores, with weights adjusted based on room type and primary use.

## 3. Parameter Thresholds by Space Type

### 3.1 Particulate Matter (PM2.5)

| Concentration (μg/m³) | Score | Condition       | Source                         |
|-----------------------|-------|-----------------|-------------------------------|
| 0-10                  | 100   | Excellent       | WHO Guidelines (2021)         |
| >10-12                | 90    | Very Good       | WELL Standard A05 (2 points)  |
| >12-15                | 80    | Good            | WELL Standard A01             |
| >15-25                | 60    | Moderate        | EPA Air Quality Index         |
| >25-35                | 40    | Poor            | WELL Standard allowable max   |
| >35                   | 20    | Very Poor       | Exceeds all standards         |

**Space-specific considerations:**
- **Conference rooms/Cafeterias**: Maintain below 12 μg/m³ due to high occupancy
- **Office spaces**: Maintain below 15 μg/m³
- **Circulation/corridors**: Acceptable up to 25 μg/m³

### 3.2 Particulate Matter (PM10)

| Concentration (μg/m³) | Score | Condition       | Source                         |
|-----------------------|-------|-----------------|-------------------------------|
| 0-20                  | 100   | Excellent       | WHO Guidelines (2021)         |
| >20-30                | 90    | Very Good       | WELL Standard A05 (2 points)  |
| >30-50                | 80    | Good            | WELL Standard A01             |
| >50-75                | 60    | Moderate        | EPA transition point           |
| >75-100               | 40    | Poor            | Exceeds recommended levels    |
| >100                  | 20    | Very Poor       | Exceeds all standards         |

### 3.3 Carbon Dioxide (CO2)

| Concentration (ppm) | Score | Condition       | Source                                |
|---------------------|-------|-----------------|--------------------------------------|
| 0-600               | 100   | Excellent       | ASHRAE recommendation                |
| >600-750            | 90    | Very Good       | WELL Standard enhanced levels        |
| >750-900            | 80    | Good            | ASHRAE Standard 62.1 recommendation |
| >900-1000           | 70    | Moderate        | WELL Standard acceptable level       |
| >1000-1500          | 50    | Poor            | Reduced cognitive function begins    |
| >1500               | 30    | Very Poor       | Significant cognitive impact         |

**Space-specific considerations:**
- **Conference rooms**: Critical monitoring (>1000 ppm requires immediate ventilation)
- **Cafeterias/dining**: Higher thresholds acceptable (up to 1200 ppm during peak times)
- **Open offices**: Maintain below 1000 ppm
- **Circulation spaces**: Less critical (up to 1200 ppm acceptable)

### 3.4 Total Volatile Organic Compounds (tVOC)

| Concentration (μg/m³) | Score | Condition       | Source                   |
|-----------------------|-------|-----------------|-------------------------|
| 0-200                 | 100   | Excellent       | Build Equinox IAQ       |
| >200-300              | 90    | Very Good       | Green building standards|
| >300-500              | 70    | Good            | WELL Standard A01       |
| >500-750              | 50    | Moderate        | Transition to poor IAQ  |
| >750-1000             | 30    | Poor            | Exceeds recommended     |
| >1000                 | 10    | Very Poor       | Health concerns possible|

**Space-specific considerations:**
- **Restrooms**: Higher threshold acceptable due to cleaning products (up to 750 μg/m³ temporarily)
- **Office spaces**: Maintain below 500 μg/m³
- **Conference rooms**: Target below 300 μg/m³ for optimal cognitive function

### 3.5 Formaldehyde (HCHO)

| Concentration (mg/m³) | Score | Condition       | Source                   |
|-----------------------|-------|-----------------|-------------------------|
| 0-0.033               | 100   | Excellent       | WELL Standard (<27 ppb) |
| >0.033-0.05           | 80    | Good            | WHO recommended limit   |
| >0.05-0.1             | 60    | Moderate        | EPA reference level     |
| >0.1-0.2              | 40    | Poor            | Health concerns possible|
| >0.2                  | 20    | Very Poor       | Significant health risk |

### 3.6 Ozone (O3)

| Concentration (ppm) | Score | Condition       | Source                             |
|---------------------|-------|-----------------|-----------------------------------|
| 0-0.02              | 100   | Excellent       | Below detection in most indoors   |
| >0.02-0.05          | 80    | Good            | WELL Standard (≤51 ppb)          |
| >0.05-0.07          | 60    | Moderate        | EPA transition point              |
| >0.07-0.09          | 40    | Poor            | Health concerns for sensitive groups |
| >0.09               | 20    | Very Poor       | Health hazard                    |

### 3.7 Ammonia (NH3) - For Restrooms (GS301 Series)

| Concentration (ppm) | Score | Condition       | Source                   |
|---------------------|-------|-----------------|-------------------------|
| 0-0.5               | 100   | Excellent       | Well below odor threshold|
| >0.5-1              | 80    | Good            | Below typical odor complaints |
| >1-5                | 60    | Moderate        | Noticeable odor, below health concern |
| >5-10               | 40    | Poor            | Strong odor, potential irritation |
| >10                 | 20    | Very Poor       | Health hazard, immediate ventilation |

**Primarily monitored in:**
- Restrooms
- Adjacent areas (for spread monitoring)
- Waste disposal areas

### 3.8 Hydrogen Sulfide (H2S) - For Restrooms (GS301 Series)

| Concentration (ppm) | Score | Condition       | Source                   |
|---------------------|-------|-----------------|-------------------------|
| 0-0.03              | 100   | Excellent       | Below typical odor threshold (CA ARB) |
| >0.03-0.1           | 80    | Good            | Noticeable odor but acceptable |
| >0.1-0.5            | 60    | Moderate        | Strong odor requiring attention |
| >0.5-2              | 40    | Poor            | Very strong odor, potential irritation |
| >2                  | 20    | Very Poor       | Health concern, immediate ventilation |

**Primarily monitored in:**
- Restrooms
- Plumbing areas
- Waste disposal areas

### 3.9 Temperature

| Value (°C)          | Score | Condition       | Source                   |
|---------------------|-------|-----------------|-------------------------|
| 20-24               | 100   | Optimal Comfort | ASHRAE Standard 55      |
| 18-20 or 24-26      | 80    | Good Comfort    | ASHRAE Expanded Range   |
| 16-18 or 26-28      | 60    | Moderate Comfort| ASHRAE Allowable Range  |
| 14-16 or 28-30      | 40    | Poor Comfort    | Outside recommended range |
| <14 or >30          | 20    | Very Poor Comfort | Health/productivity concerns |

**Space-specific recommendations:**
- **Office spaces**: 20-24°C optimal
- **Conference rooms**: 20-23°C optimal for alertness
- **Cafeterias**: 22-26°C acceptable
- **Circulation areas**: 18-26°C acceptable
- **Restrooms**: 19-26°C acceptable

### 3.10 Relative Humidity

| Value (%RH)         | Score | Condition       | Source                   |
|---------------------|-------|-----------------|-------------------------|
| 40-50               | 100   | Optimal         | ASHRAE optimal range    |
| 30-40 or 50-60      | 80    | Good            | WELL Standard T07       |
| 20-30 or 60-70      | 60    | Moderate        | ASHRAE allowable range  |
| 10-20 or 70-80      | 40    | Poor            | Potential for discomfort|
| <10 or >80          | 20    | Very Poor       | Health/building concerns|

**Space-specific recommendations:**
- **Office spaces**: 30-60%
- **Restrooms**: 30-60% (mold prevention critical)
- **Conference rooms**: 40-50% for optimal comfort
- **Storage areas**: 30-50% to prevent mold/material damage

## 4. Weighted Calculation Method by Space Type

### 4.1 Office/Cubicle (275,000 sq ft)

| Parameter | Weight | Justification                              |
|-----------|--------|--------------------------------------------|
| PM2.5     | 15%    | Health impact in sedentary environments    |
| PM10      | 10%    | Less critical than PM2.5 for office workers|
| CO2       | 25%    | Critical for cognitive function           |
| tVOC      | 15%    | Important for productivity and comfort    |
| HCHO/O3   | 10%    | Health irritant                           |
| Temperature | 15%  | Significant impact on productivity        |
| Humidity  | 10%    | Comfort factor                            |

### 4.2 Conference/Meeting Rooms (20,000 sq ft)

| Parameter | Weight | Justification                              |
|-----------|--------|--------------------------------------------|
| PM2.5     | 15%    | Health impact in enclosed spaces          |
| PM10      | 10%    | Less critical than PM2.5                 |
| CO2       | 30%    | Crucial for cognitive function           |
| tVOC      | 15%    | Important for productivity and comfort    |
| HCHO/O3   | 5%     | Less variant in these spaces             |
| Temperature | 15%  | Critical for meeting comfort             |
| Humidity  | 10%    | Comfort factor                            |

### 4.3 Restrooms (12,500 sq ft)

| Parameter | Weight | Justification                              |
|-----------|--------|--------------------------------------------|
| PM2.5     | 5%     | Less critical in frequently ventilated space |
| PM10      | 5%     | Less critical in frequently ventilated space |
| NH3       | 25%    | Critical for odor control                 |
| H2S       | 25%    | Critical for odor control                 |
| tVOC      | 15%    | Important due to cleaning products        |
| Temperature | 10%  | Comfort factor                           |
| Humidity  | 15%    | Critical for mold prevention             |

### 4.4 Office Circulation/Walkways (90,000 sq ft)

| Parameter | Weight | Justification                              |
|-----------|--------|--------------------------------------------|
| PM2.5     | 20%    | Important in high-traffic areas           |
| PM10      | 20%    | Important for larger dust particles       |
| CO2       | 10%    | Less critical in transit spaces          |
| tVOC      | 15%    | Moderate importance                      |
| Temperature | 15%  | Comfort during transit                   |
| Humidity  | 10%    | Less critical than in occupied spaces    |
| HCHO/O3   | 10%    | Health irritant                          |

### 4.5 Corridors/Common Areas (50,000 sq ft)

| Parameter | Weight | Justification                              |
|-----------|--------|--------------------------------------------|
| PM2.5     | 20%    | Important in high-traffic areas           |
| PM10      | 20%    | Important for larger dust particles       |
| CO2       | 15%    | Moderate importance in shared areas      |
| tVOC      | 15%    | Moderate importance                      |
| Temperature | 15%  | Comfort in gathering areas              |
| Humidity  | 10%    | Comfort factor                           |
| HCHO/O3   | 5%     | Less critical than in occupied spaces    |

### 4.6 Cafeteria/Dining Area (10,000 sq ft)

| Parameter | Weight | Justification                              |
|-----------|--------|--------------------------------------------|
| PM2.5     | 15%    | Health impact in high-occupancy space    |
| PM10      | 15%    | Relevant for food particles              |
| CO2       | 20%    | Important for high occupancy             |
| tVOC      | 10%    | Less critical than offices               |
| Temperature | 20%  | Critical for dining comfort             |
| Humidity  | 10%    | Comfort factor                           |
| HCHO/O3   | 10%    | Health irritant                          |

### 4.7 Other Areas (42,500 sq ft)

| Parameter | Weight | Justification                              |
|-----------|--------|--------------------------------------------|
| PM2.5     | 15%    | General health consideration             |
| PM10      | 15%    | General health consideration             |
| CO2       | 15%    | Moderate importance                     |
| tVOC      | 15%    | Moderate importance                     |
| Temperature | 15%  | General comfort                        |
| Humidity  | 15%    | General comfort and building health     |
| HCHO/O3   | 10%    | Health irritant                         |

## 5. Score Calculation Formula

### 5.1 Individual Parameter Score

For each parameter:
- Parameter Score = Lookup score from appropriate threshold table

### 5.2 Room-specific Air Quality Score

Room AQ Score = Σ (Parameter Score × Parameter Weight for room type)

### 5.3 Overall Building Air Quality Score

Building AQ Score = Σ (Room AQ Score × Room square footage) / Total square footage

## 6. Automated Cleaning Task Generation

### 6.1 Scoring Triggers by Space Type

| Space Type         | Score Trigger | Action Required                              | Priority |
|--------------------|---------------|---------------------------------------------|----------|
| **Office/Cubicle** | <70           | Enhanced cleaning                           | Medium   |
|                    | <50           | Deep cleaning + ventilation check           | High     |
|                    | <40           | Immediate deep cleaning + source investigation | Urgent |
| **Conference Room**| <80           | Enhanced cleaning before next meeting       | Medium   |
|                    | <60           | Deep cleaning + ventilation boost           | High     |
|                    | <40           | Room closure until remediated               | Urgent   |
| **Restrooms**      | <70           | Additional cleaning                        | Medium   |
|                    | <50           | Deep cleaning + ventilation boost           | High     |
|                    | <40           | Immediate servicing + plumbing check        | Urgent   |
| **Circulation Areas** | <60        | Enhanced cleaning                           | Medium   |
|                    | <40           | Deep cleaning + ventilation check           | High     |
| **Cafeteria**      | <70           | Enhanced cleaning                           | Medium   |
|                    | <50           | Deep cleaning + ventilation adjustment      | High     |
|                    | <40           | Service interruption + remediation          | Urgent   |

### 6.2 Parameter-Specific Protocols

**High Particulate Matter (PM2.5, PM10):**
- Increase vacuuming frequency with HEPA filters
- Check HVAC filtration
- Inspect for dust sources
- Damp wiping of surfaces

**High CO2:**
- Increase fresh air ventilation
- Verify occupancy vs. ventilation rate
- Check HVAC operation
- Consider occupancy limits for conference rooms

**High tVOC:**
- Identify potential sources (furniture, cleaning products)
- Increase ventilation
- Review cleaning product selection
- Schedule cleaning during unoccupied hours

**High NH3 or H2S in Restrooms:**
- Immediate deep cleaning
- Check drain traps and plumbing
- Verify exhaust fan operation
- Increase ventilation rates
- Consider plumbing inspection if persistent

**Temperature/Humidity Issues:**
- Verify HVAC settings and operation
- Check for envelope issues (infiltration)
- Adjust ventilation rates
- Monitor for mold in high humidity areas

## 7. Implementation and Maintenance

### 7.1 Sensor Placement Guidelines

| Space Type         | Sensor Type | Recommended Placement                   | Density                  |
|--------------------|-------------|----------------------------------------|--------------------------|
| Office/Cubicle     | AM300       | Central location, breathing height      | 1 per 1,000-2,000 sq ft  |
| Conference Room    | AM300       | Wall-mounted, opposite HVAC supply      | 1 per room >300 sq ft    |
| Restrooms          | GS301       | Near exhaust, avoiding direct spray     | 1 per restroom           |
| Circulation        | AM300       | Key junction points                    | 1 per 3,000-5,000 sq ft |
| Cafeteria          | AM300       | Multiple zones including seating & service | 1 per 1,000 sq ft    |

### 7.2 Calibration Schedule

| Sensor Type | Parameter       | Calibration Frequency | Method                     |
|-------------|-----------------|----------------------|---------------------------|
| AM300       | PM2.5/PM10      | Quarterly            | Reference instrument comparison |
| AM300       | CO2             | Semi-annually        | Calibration gas           |
| AM300       | tVOC            | Semi-annually        | Calibration gas           |
| AM300       | Temp/Humidity   | Annually             | Reference device          |
| GS301       | NH3/H2S         | Quarterly            | Calibration gas           |

### 7.3 Data Validation Procedures

- Implement automated outlier detection
- Cross-validate between nearby sensors
- Flag sudden extreme changes for investigation
- Regular data quality audits

## 8. Reporting and Analysis

### 8.1 Dashboard Components

- Overall building score
- Space-specific scores with trend analysis
- Parameter-specific visualizations
- Automated task generation log
- Compliance tracking against standards

### 8.2 Reporting Schedule

- Real-time alerts for urgent conditions
- Daily summary for facility management
- Weekly trend analysis
- Monthly comprehensive report
- Quarterly performance review

## 9. Sources and References

- [WELL Building Standard v2](https://standard.wellcertified.com/air/air-quality-standards)
- ASHRAE Standard 55-2020: Thermal Environmental Conditions for Human Occupancy
- ASHRAE Standard 62.1-2019: Ventilation for Acceptable Indoor Air Quality
- WHO Global Air Quality Guidelines (2021)
- EPA Indoor Air Quality Guidelines
- California Air Resources Board H2S Standards
- NIOSH Recommended Exposure Limits
- Build Equinox IAQ Standards
- OSHA Permissible Exposure Limits
- RESET Air Standard

This system provides a tailored approach to monitoring and improving indoor air quality, informing cleaning protocols and ventilation adjustments while aligning with established health standards.