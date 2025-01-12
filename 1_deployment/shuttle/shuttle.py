from shuttle import ShuttleBase, ShuttleConfig, process_modes

def main():
    
    scanner = None
    
    config = ShuttleBase.parse_config()
    
    if config.process_mode == process_modes.PASSIVE:
        from shuttle_passive import PassiveScanner
        scanner = PassiveScanner(config)
    else:
        from shuttle_active import ActiveScanner
        scanner = ActiveScanner(config)
        
    scanner.main()  


if __name__ == '__main__':
    main()