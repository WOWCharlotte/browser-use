interface Props {
	message: string;
	options: string[];
	onSelect: (option: string) => void;
}

export function ConfirmDialog({ message, options, onSelect }: Props) {
	return (
		<div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 backdrop-blur-sm">
			<div className="bg-white rounded-2xl p-6 shadow-xl max-w-sm text-center animate-in">
				<div className="w-11 h-11 rounded-full bg-red-100 text-red-500 flex items-center justify-center mx-auto mb-4">
					<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
						<circle cx="12" cy="12" r="10" />
						<line x1="12" y1="8" x2="12" y2="12" />
						<line x1="12" y1="16" x2="12.01" y2="16" />
					</svg>
				</div>
				<h3 className="font-semibold text-base mb-2">Confirm Action</h3>
				<p className="text-sm text-gray-500 mb-5">{message}</p>
				<div className="flex gap-2 justify-center">
					{options.map((option) => (
						<button
							key={option}
							onClick={() => onSelect(option)}
							className={`px-4 py-1.5 rounded-full text-sm font-medium transition-colors ${
								option === "confirm"
									? "bg-red-500 text-white hover:bg-red-600"
									: "bg-gray-100 text-gray-600 hover:bg-gray-200"
							}`}
						>
							{option}
						</button>
					))}
				</div>
			</div>
		</div>
	);
}