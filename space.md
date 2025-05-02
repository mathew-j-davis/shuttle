```python  
                # Check disk space if throttling is enabled
                if throttle:
                    try:
                        # Get file size in MB
                        file_size_mb = os.path.getsize(source_file_path) / (1024 * 1024)
                        
                        # Check quarantine space
                        if not quarantine_full:
                        stats = shutil.disk_usage(quarantine_path)
                        free_mb = stats.free / (1024 * 1024)
                        if (free_mb - file_size_mb) < throttle_free_space:
                            logger.error(f"Quarantine directory is full. Free: {free_mb:.2f} MB, Required: {throttle_free_space + file_size_mb:.2f} MB")
                            quarantine_full = True
                        
                        # Check destination space
                        if not destination_full:
                            stats = shutil.disk_usage(destination_path)
                            free_mb = stats.free / (1024 * 1024)
                            if (free_mb - file_size_mb) < throttle_free_space:
                                logger.error(f"Destination directory is full. Free: {free_mb:.2f} MB, Required: {throttle_free_space + file_size_mb:.2f} MB")
                                destination_full = True
                        
                        # Check hazard archive space if applicable
                        if hazard_archive_path and not hazard_full:
                            if not os.path.exists(hazard_archive_path):
                                os.makedirs(hazard_archive_path, exist_ok=True)
                            stats = shutil.disk_usage(hazard_archive_path)
                            free_mb = stats.free / (1024 * 1024)
                            if (free_mb - file_size_mb) < throttle_free_space:
                                logger.error(f"Hazard archive directory is full. Free: {free_mb:.2f} MB, Required: {throttle_free_space + file_size_mb:.2f} MB")
                                hazard_full = True
                        
                        # If any directory is full, break out of the inner loop
                        if quarantine_full or destination_full or hazard_full:
                            logger.warning(f"Stopping file processing due to insufficient disk space")
                            break
                            
                    except Exception as e:
                        logger.error(f"Error checking disk space: {e}")

                # If directories are full, don't process more files
                if quarantine_full or destination_full or hazard_full:
                    break

```