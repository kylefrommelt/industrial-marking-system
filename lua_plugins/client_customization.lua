-- Client Customization Plugin
-- Demonstrates custom Lua solutions for specific client requirements
-- Shows extensibility and client-focused development approach

local ClientCustomization = {}
ClientCustomization.__index = ClientCustomization

-- Client-specific configuration
local CLIENT_CONFIGS = {
    automotive = {
        name = "Automotive Component Marking",
        date_format = "%Y%m%d",
        serial_format = "AUTO-{SERIAL:8}",
        quality_requirements = "automotive_grade",
        regulatory_compliance = {"IATF16949", "ISO9001"},
        marking_positions = {
            primary = {x = 5, y = 5},
            secondary = {x = 20, y = 5}
        }
    },
    medical_device = {
        name = "Medical Device Identification",
        date_format = "%d%b%Y",
        serial_format = "MDI-{LOT}-{SERIAL:6}",
        quality_requirements = "medical_grade",
        regulatory_compliance = {"FDA_UDI", "ISO13485", "MDR"},
        marking_positions = {
            primary = {x = 3, y = 3},
            udi_code = {x = 3, y = 8}
        }
    },
    food_packaging = {
        name = "Food Packaging Traceability",
        date_format = "%d/%m/%y",
        serial_format = "FP{DATE}{SHIFT}{SERIAL:4}",
        quality_requirements = "food_safe",
        regulatory_compliance = {"FDA_FSMA", "HACCP"},
        marking_positions = {
            expiry_date = {x = 10, y = 2},
            lot_code = {x = 10, y = 7}
        }
    }
}

-- Constructor
function ClientCustomization:new(client_type, custom_config)
    local instance = {
        client_type = client_type,
        config = CLIENT_CONFIGS[client_type] or {},
        custom_config = custom_config or {},
        marking_history = {},
        validation_rules = {},
        performance_metrics = {
            marks_processed = 0,
            validation_failures = 0,
            average_processing_time = 0
        }
    }
    
    -- Override with custom configuration
    if custom_config then
        for key, value in pairs(custom_config) do
            instance.config[key] = value
        end
    end
    
    setmetatable(instance, ClientCustomization)
    instance:initialize_validation_rules()
    return instance
end

-- Initialize client-specific validation rules
function ClientCustomization:initialize_validation_rules()
    if self.client_type == "automotive" then
        self:setup_automotive_validation()
    elseif self.client_type == "medical_device" then
        self:setup_medical_validation()
    elseif self.client_type == "food_packaging" then
        self:setup_food_packaging_validation()
    end
end

-- Automotive industry validation
function ClientCustomization:setup_automotive_validation()
    self.validation_rules = {
        serial_number = function(serial)
            return string.len(serial) >= 6 and string.match(serial, "^[A-Z0-9]+$")
        end,
        part_number = function(part)
            return string.match(part, "^[A-Z]{2}%-[0-9]{4,6}%-[A-Z0-9]{2}$")
        end,
        supplier_code = function(code)
            return string.len(code) == 4 and string.match(code, "^[A-Z]{4}$")
        end
    }
end

-- Medical device validation
function ClientCustomization:setup_medical_validation()
    self.validation_rules = {
        udi_code = function(udi)
            -- Basic UDI format validation
            return string.len(udi) >= 14 and string.match(udi, "^[0-9A-Z]+$")
        end,
        lot_number = function(lot)
            return string.len(lot) >= 3 and string.len(lot) <= 20
        end,
        expiry_date = function(date)
            return string.match(date, "^%d%d%d%d%-%d%d%-%d%d$")
        end
    }
end

-- Food packaging validation
function ClientCustomization:setup_food_packaging_validation()
    self.validation_rules = {
        production_date = function(date)
            return string.match(date, "^%d%d/%d%d/%d%d$")
        end,
        shift_code = function(shift)
            return shift == "A" or shift == "B" or shift == "C"
        end,
        line_number = function(line)
            local num = tonumber(line)
            return num and num >= 1 and num <= 10
        end
    }
end

-- Process marking request with client-specific logic
function ClientCustomization:process_marking_request(product_data)
    local start_time = os.clock()
    
    -- Validate input data
    local validation_result = self:validate_product_data(product_data)
    if not validation_result.valid then
        self.performance_metrics.validation_failures = 
            self.performance_metrics.validation_failures + 1
        return {
            success = false,
            error = validation_result.error,
            client_type = self.client_type
        }
    end
    
    -- Generate marking content based on client requirements
    local marking_content = self:generate_client_marking(product_data)
    
    -- Apply client-specific formatting
    local formatted_content = self:apply_client_formatting(marking_content, product_data)
    
    -- Record marking for traceability
    self:record_marking(product_data, formatted_content)
    
    -- Update performance metrics
    local processing_time = os.clock() - start_time
    self:update_performance_metrics(processing_time)
    
    return {
        success = true,
        marking_content = formatted_content,
        client_type = self.client_type,
        processing_time = processing_time,
        compliance_info = self:get_compliance_info()
    }
end

-- Validate product data against client rules
function ClientCustomization:validate_product_data(data)
    for field, validator in pairs(self.validation_rules) do
        local value = data[field]
        if value and not validator(value) then
            return {
                valid = false,
                error = string.format("Invalid %s: %s", field, tostring(value))
            }
        end
    end
    
    -- Client-specific additional validation
    if self.client_type == "medical_device" then
        return self:validate_medical_device_data(data)
    elseif self.client_type == "automotive" then
        return self:validate_automotive_data(data)
    end
    
    return {valid = true}
end

-- Medical device specific validation
function ClientCustomization:validate_medical_device_data(data)
    -- Check UDI requirements
    if not data.udi_code and not (data.device_identifier and data.production_identifier) then
        return {
            valid = false,
            error = "UDI code or device/production identifiers required for medical devices"
        }
    end
    
    -- Validate expiry date is in future
    if data.expiry_date then
        local current_date = os.date("%Y-%m-%d")
        if data.expiry_date <= current_date then
            return {
                valid = false,
                error = "Expiry date must be in the future"
            }
        end
    end
    
    return {valid = true}
end

-- Automotive specific validation
function ClientCustomization:validate_automotive_data(data)
    -- Check required automotive fields
    local required_fields = {"part_number", "supplier_code", "serial_number"}
    for _, field in ipairs(required_fields) do
        if not data[field] then
            return {
                valid = false,
                error = string.format("Required field missing: %s", field)
            }
        end
    end
    
    return {valid = true}
end

-- Generate client-specific marking content
function ClientCustomization:generate_client_marking(product_data)
    local content = {}
    
    if self.client_type == "automotive" then
        content = self:generate_automotive_marking(product_data)
    elseif self.client_type == "medical_device" then
        content = self:generate_medical_device_marking(product_data)
    elseif self.client_type == "food_packaging" then
        content = self:generate_food_packaging_marking(product_data)
    else
        -- Generic marking
        content = {
            text = string.format("S/N: %s Date: %s", 
                   product_data.serial_number or "N/A",
                   os.date(self.config.date_format or "%Y-%m-%d")),
            position = self.config.marking_positions.primary or {x = 10, y = 10}
        }
    end
    
    return content
end

-- Automotive marking generation
function ClientCustomization:generate_automotive_marking(data)
    local formatted_serial = self.config.serial_format:gsub("{SERIAL:(%d+)}", 
        function(length)
            return string.format("%0" .. length .. "s", data.serial_number:sub(1, tonumber(length)))
        end)
    
    return {
        primary_mark = {
            text = string.format("%s\n%s\n%s", 
                   data.part_number,
                   formatted_serial,
                   data.supplier_code),
            position = self.config.marking_positions.primary,
            font_size = 8,
            quality = "automotive_grade"
        },
        secondary_mark = {
            text = os.date(self.config.date_format),
            position = self.config.marking_positions.secondary,
            font_size = 6,
            quality = "automotive_grade"
        }
    }
end

-- Medical device marking generation
function ClientCustomization:generate_medical_device_marking(data)
    local udi_text = data.udi_code or 
                    string.format("(01)%s(17)%s(10)%s", 
                                  data.device_identifier or "",
                                  data.expiry_date or "",
                                  data.lot_number or "")
    
    return {
        udi_mark = {
            text = udi_text,
            position = self.config.marking_positions.udi_code,
            font_size = 6,
            quality = "medical_grade"
        },
        primary_mark = {
            text = string.format("LOT: %s\nEXP: %s", 
                   data.lot_number or "",
                   data.expiry_date or ""),
            position = self.config.marking_positions.primary,
            font_size = 8,
            quality = "medical_grade"
        }
    }
end

-- Food packaging marking generation
function ClientCustomization:generate_food_packaging_marking(data)
    local production_date = os.date(self.config.date_format)
    local shift = data.shift_code or "A"
    local line = data.line_number or "1"
    
    return {
        expiry_mark = {
            text = string.format("BEST BY: %s", data.expiry_date or ""),
            position = self.config.marking_positions.expiry_date,
            font_size = 10,
            quality = "food_safe"
        },
        lot_mark = {
            text = string.format("LOT: %s%s%s%04d", 
                   production_date:gsub("/", ""),
                   shift,
                   line,
                   data.serial_number or 0),
            position = self.config.marking_positions.lot_code,
            font_size = 8,
            quality = "food_safe"
        }
    }
end

-- Apply client-specific formatting
function ClientCustomization:apply_client_formatting(content, data)
    -- Add client-specific formatting rules
    for mark_name, mark_data in pairs(content) do
        if mark_data.text then
            -- Apply text transformations
            mark_data.text = self:apply_text_formatting(mark_data.text, data)
            
            -- Add compliance prefixes if required
            if self:requires_compliance_prefix(mark_name) then
                mark_data.text = self:add_compliance_prefix(mark_data.text)
            end
        end
    end
    
    return content
end

-- Apply text formatting rules
function ClientCustomization:apply_text_formatting(text, data)
    -- Replace placeholders with actual data
    text = text:gsub("{DATE}", os.date(self.config.date_format))
    text = text:gsub("{SERIAL}", data.serial_number or "")
    text = text:gsub("{LOT}", data.lot_number or "")
    text = text:gsub("{SHIFT}", data.shift_code or "")
    
    return text
end

-- Record marking for traceability
function ClientCustomization:record_marking(product_data, marking_content)
    local record = {
        timestamp = os.time(),
        product_data = product_data,
        marking_content = marking_content,
        client_type = self.client_type,
        compliance_standards = self.config.regulatory_compliance
    }
    
    table.insert(self.marking_history, record)
    
    -- Limit history size
    if #self.marking_history > 1000 then
        table.remove(self.marking_history, 1)
    end
end

-- Update performance metrics
function ClientCustomization:update_performance_metrics(processing_time)
    self.performance_metrics.marks_processed = 
        self.performance_metrics.marks_processed + 1
    
    local total_time = self.performance_metrics.average_processing_time * 
                      (self.performance_metrics.marks_processed - 1) + processing_time
    self.performance_metrics.average_processing_time = 
        total_time / self.performance_metrics.marks_processed
end

-- Get compliance information
function ClientCustomization:get_compliance_info()
    return {
        standards = self.config.regulatory_compliance or {},
        client_type = self.client_type,
        quality_level = self.config.quality_requirements,
        validation_rules_count = self:count_table(self.validation_rules)
    }
end

-- Utility function to count table entries
function ClientCustomization:count_table(t)
    local count = 0
    for _ in pairs(t) do count = count + 1 end
    return count
end

-- Check if compliance prefix is required
function ClientCustomization:requires_compliance_prefix(mark_name)
    return self.client_type == "medical_device" and mark_name:find("udi")
end

-- Add compliance prefix to text
function ClientCustomization:add_compliance_prefix(text)
    if self.client_type == "medical_device" then
        return "(01)" .. text
    end
    return text
end

-- Get performance report
function ClientCustomization:get_performance_report()
    return {
        client_type = self.client_type,
        metrics = self.performance_metrics,
        validation_success_rate = (self.performance_metrics.marks_processed - 
                                 self.performance_metrics.validation_failures) / 
                                math.max(self.performance_metrics.marks_processed, 1),
        marking_history_count = #self.marking_history
    }
end

return ClientCustomization 