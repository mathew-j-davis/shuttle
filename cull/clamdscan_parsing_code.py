
            # the code below is not required as clamdscan returns the scan result as return code, however it may be useful for debugging
            
            # output.strip()

            # # Always check for threat and error pattern first, otherwise a malicous filename could be used to add clean response text to output
            # # Check for threat found pattern
            # if re.search(clamav_parse_response_patterns.THREAT_FOUND, output):
            #     logger.warning(f"Threats found in {path}")
            #     return scan_result_types.FILE_IS_SUSPECT
            
            # # Check for error pattern
            # if re.search(clamav_parse_response_patterns.ERROR, output):
            #     return scan_result_types.FILE_SCAN_FAILED
            
            # # Check for clean scan pattern

            # parsed_filename = output.split(': ')[0]
            # remaining = output.split(': ')[1:]

            # if isinstance(remaining,str):
            #     result_text = remaining
            # else:
            #     result_text = "".join(remaining)

            # if parsed_filename != path:
            #     logger.warning(f"Unexpected scan output for {path}: {output}")
            #     return scan_result_types.FILE_SCAN_FAILED
            
            # if  re.search(clamav_parse_response_patterns.OK, result_text) and clamav_parse_response_patterns.NO_THREATS in output:
            #     logger.info(f"No threat found in {path}")
            #     return scan_result_types.FILE_IS_CLEAN
            
            # # Output doesn't match expected patterns
            # else:
            #     logger.warning(f"Unexpected scan output for {path}: {output}")