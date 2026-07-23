import React from 'react';
import { cn } from "../lib/utils";

export function Button({ className, ...props }: React.ComponentProps<'button'>) {
    return (
        <button
            className={cn(
                'cursor-pointer',
                className
            )}
            {...props}
        />
    )
}