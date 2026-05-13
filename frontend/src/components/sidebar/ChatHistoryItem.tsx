import { useState, KeyboardEvent } from "react";
import { Session } from "@/types";
import { updateSession } from "@/lib/api";

const TITLE_MAX_LENGTH = 20;
const TITLE_PATTERN = /^[a-zA-Z0-9一-龥\s]+$/;

interface Props {
	session: Session;
	isActive: boolean;
	onClick: () => void;
	onDelete: () => void;
	onTitleChange?: (sessionId: string, newTitle: string) => void;
}

export function ChatHistoryItem({ session, isActive, onClick, onDelete, onTitleChange }: Props) {
	const [isEditing, setIsEditing] = useState(false);
	const [editValue, setEditValue] = useState(session.title);
	const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
	const [error, setError] = useState("");
	const [showErrorPopup, setShowErrorPopup] = useState(false);

	const validateTitle = (title: string): string => {
		if (!title.trim()) return "Title cannot be empty";
		if (title.length > TITLE_MAX_LENGTH) return `Title must be ${TITLE_MAX_LENGTH} characters or less`;
		if (!TITLE_PATTERN.test(title)) return "No special characters allowed";
		return "";
	};

	const handleSave = async () => {
		const trimmed = editValue.trim();
		const validationError = validateTitle(trimmed);
		if (validationError) {
			setError(validationError);
			setShowErrorPopup(true);
			return;
		}
		setError("");
		setShowErrorPopup(false);
		if (trimmed && trimmed !== session.title) {
			try {
				await updateSession(session.id, trimmed);
				onTitleChange?.(session.id, trimmed);
			} catch (e) {
				console.error("Failed to update session title:", e);
			}
		}
		setIsEditing(false);
	};

	const handleEdit = () => {
		setIsEditing(true);
		setEditValue(session.title);
		setError("");
		setShowErrorPopup(false);
	};

	const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
		if (e.key === "Enter") {
			handleSave();
		} else if (e.key === "Escape") {
			setIsEditing(false);
			setEditValue(session.title);
			setError("");
			setShowErrorPopup(false);
		}
	};

	const handleDeleteClick = (e: React.MouseEvent) => {
		e.stopPropagation();
		setShowDeleteConfirm(true);
	};

	const handleConfirmDelete = () => {
		setShowDeleteConfirm(false);
		onDelete();
	};

	const handleCancelDelete = () => {
		setShowDeleteConfirm(false);
	};

	const handleDoubleClick = (e: React.MouseEvent) => {
		e.stopPropagation();
		setIsEditing(true);
		setEditValue(session.title);
		setError("");
		setShowErrorPopup(false);
	};

	const handleDismissError = () => {
		setShowErrorPopup(false);
	};

	return (
		<>
			<div
				onClick={onClick}
				onDoubleClick={handleDoubleClick}
				className={`flex items-center gap-2 px-3 py-1.5 rounded cursor-pointer group ${
					isActive ? "bg-blue-50" : "hover:bg-gray-100"
				}`}
			>
				<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className={isActive ? "text-blue-500" : "text-gray-400"}>
					<path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
				</svg>
				{isEditing ? (
					<div className="flex-1">
						<input
							type="text"
							value={editValue}
							onChange={(e) => {
								setEditValue(e.target.value);
								setError("");
							}}
							onBlur={handleSave}
							onKeyDown={handleKeyDown}
							onClick={(e) => e.stopPropagation()}
							autoFocus
							title={`Max ${TITLE_MAX_LENGTH} characters, no special characters`}
							className={`w-full text-sm px-1 py-0.5 border rounded outline-none ${error ? "border-red-400" : "border-blue-400"}`}
						/>
					</div>
				) : (
					<span className={`flex-1 text-sm truncate ${isActive ? "text-blue-600 font-medium" : "text-gray-600"}`}>
						{session.title}
					</span>
				)}
				<button
					type="button"
					onClick={(e) => { e.stopPropagation(); handleEdit(); }}
					className="opacity-0 group-hover:opacity-100 w-5 h-5 rounded hover:bg-blue-100 flex items-center justify-center text-gray-400 hover:text-blue-500"
					title="Edit title"
				>
					<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
						<path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" />
						<path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" />
					</svg>
				</button>
				<button
					type="button"
					onClick={handleDeleteClick}
					className="opacity-0 group-hover:opacity-100 w-5 h-5 rounded hover:bg-red-100 flex items-center justify-center text-gray-400 hover:text-red-500"
					title="Delete session"
				>
					<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
						<polyline points="3 6 5 6 21 6" />
						<path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6" />
					</svg>
				</button>
			</div>
			{showDeleteConfirm && (
				<div className="fixed inset-0 bg-black/30 flex items-center justify-center z-50">
					<div className="bg-white rounded-lg p-4 shadow-xl max-w-xs">
						<h3 className="text-sm font-medium text-gray-900 mb-2">Confirm Delete</h3>
						<p className="text-xs text-gray-500 mb-4">Are you sure you want to delete "{session.title}"?</p>
						<div className="flex justify-end gap-2">
							<button
								type="button"
								onClick={handleCancelDelete}
								className="px-3 py-1.5 text-xs text-gray-600 hover:bg-gray-100 rounded"
							>
								Cancel
							</button>
							<button
								type="button"
								onClick={handleConfirmDelete}
								className="px-3 py-1.5 text-xs text-white bg-red-500 hover:bg-red-600 rounded"
							>
								Delete
							</button>
						</div>
					</div>
				</div>
			)}
			{showErrorPopup && (
				<div className="fixed inset-0 bg-black/30 flex items-center justify-center z-50">
					<div className="bg-white rounded-lg p-4 shadow-xl max-w-xs">
						<div className="flex items-center gap-2 mb-2">
							<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#ef4444" strokeWidth="2">
								<circle cx="12" cy="12" r="10" />
								<line x1="12" y1="8" x2="12" y2="12" />
								<line x1="12" y1="16" x2="12.01" y2="16" />
							</svg>
							<h3 className="text-sm font-medium text-gray-900">Invalid Title</h3>
						</div>
						<p className="text-xs text-gray-500 mb-3">{error}</p>
						<button
							type="button"
							onClick={handleDismissError}
							className="w-full px-3 py-1.5 text-xs text-gray-600 hover:bg-gray-100 rounded"
						>
							OK
						</button>
					</div>
				</div>
			)}
		</>
	);
}