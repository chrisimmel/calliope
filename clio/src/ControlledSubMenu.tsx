import { ReactNode, useRef, useState } from 'react';
import { MenuItem, MenuButton, MenuRadioGroup, SubMenu, ControlledMenu, useClick } from '@szhsin/react-menu';
import '@szhsin/react-menu/dist/core.css';
import '@szhsin/react-menu/dist/index.css';
import '@szhsin/react-menu/dist/theme-dark.css';
import './Toolbar.css';

import IconChevronLeft from './icons/IconChevronLeft';

type ControlledSubMenuProps = {
    label: string,
    children: ReactNode,
}


export function ControlledSubMenu({
    label,
    children,
}: ControlledSubMenuProps) {
    const ref = useRef(null);
    const [isOpen, setOpen] = useState(false);
  
    return (
        <>
            <MenuItem
                ref={ref}
                onClick={(e) => {
                    setOpen(true);
                    // Keep the menu open after this menu item is clicked.
                    e.keepOpen = true;
                }}
            >
                {label}
            </MenuItem>
            <ControlledMenu
                state={isOpen ? 'open' : 'closed'}
                anchorRef={ref}
                onClose={() => setOpen(false)}
                portal={true}
            >
                <MenuItem className="backMenu">
                    <IconChevronLeft/>
                </MenuItem>
                {children}
            </ControlledMenu>
        </>
    );
}
