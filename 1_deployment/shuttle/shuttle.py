from shuttle import ShuttleBase, ShuttleConfig, process_modes
from shuttle_active import ActiveScanner

def main():
    
    scanner = None
    
    config = ShuttleBase.parse_config()
    
    scanner = ActiveScanner(config)
        
    scanner.main()  

if __name__ == '__main__':
    main()