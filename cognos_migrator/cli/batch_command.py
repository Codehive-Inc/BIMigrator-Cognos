"""
Batch Migration Command Handler

Handles batch-migrate command.
Follows Single Responsibility Principle.
"""

import os
from typing import Any
from .base_command import BaseCommandHandler


class BatchMigrationCommandHandler(BaseCommandHandler):
    """Handler for batch-migrate command"""
    
    def execute(self, args: Any) -> bool:
        """Execute batch-migrate command"""
        self.logger.info(f"Batch migrating modules from {args.modules_file}...")
        
        try:
            # Read module IDs
            module_ids = self._read_modules_file(args.modules_file)
            if not module_ids:
                return False
            
            # Process modules
            success_count = 0
            enhanced_main = self.lazy_imports.get_enhanced_main()
            
            for i, module_id in enumerate(module_ids, 1):
                print(f"\n[{i}/{len(module_ids)}] Processing module {module_id}...")
                
                output_path = os.path.join(args.output_base_path, module_id)
                
                try:
                    result = enhanced_main['migrate_module'](
                        module_id=module_id,
                        output_path=output_path,
                        cognos_url=args.cognos_url,
                        session_key=args.session_key,
                        enable_enhanced_validation=getattr(args, 'enable_enhanced_validation', False)
                    )
                    
                    if result['success']:
                        success_count += 1
                        print(f"  ✓ Success")
                    else:
                        print(f"  ✗ Failed: {result.get('error', 'Unknown error')}")
                        
                except Exception as e:
                    print(f"  ✗ Exception: {e}")
                    
                    if not getattr(args, 'continue_on_error', False):
                        break
            
            # Print summary
            self._print_batch_summary(len(module_ids), success_count)
            
            return success_count == len(module_ids)
            
        except Exception as e:
            self.logger.error(f"Batch migration failed: {e}")
            return False
    
    def _read_modules_file(self, file_path: str) -> list:
        """Read module IDs from file"""
        try:
            with open(file_path, 'r') as f:
                return [line.strip() for line in f if line.strip()]
        except Exception as e:
            self.logger.error(f"Failed to read modules file: {e}")
            return []
    
    def _print_batch_summary(self, total: int, success_count: int):
        """Print batch migration summary"""
        print(f"\n=== Batch Migration Summary ===")
        print(f"Total modules: {total}")
        print(f"Successful: {success_count}")
        print(f"Failed: {total - success_count}")
        print(f"Success rate: {(success_count / total * 100):.1f}%")