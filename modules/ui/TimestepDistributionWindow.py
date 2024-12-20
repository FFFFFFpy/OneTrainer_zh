from modules.modelSetup.mixin.ModelSetupNoiseMixin import ModelSetupNoiseMixin
from modules.util.config.TrainConfig import TrainConfig
from modules.util.enum.TimestepDistribution import TimestepDistribution
from modules.util.ui import components
from modules.util.ui.UIState import UIState

import torch
from torch import Tensor

import customtkinter as ctk
from customtkinter import AppearanceModeTracker, ThemeManager
from matplotlib import pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg


class TimestepGenerator(ModelSetupNoiseMixin):

    def __init__(
            self,
            timestep_distribution: TimestepDistribution,
            min_noising_strength: float,
            max_noising_strength: float,
            noising_weight: float,
            noising_bias: float,
    ):
        super().__init__()

        self.timestep_distribution = timestep_distribution
        self.min_noising_strength = min_noising_strength
        self.max_noising_strength = max_noising_strength
        self.noising_weight = noising_weight
        self.noising_bias = noising_bias

    def generate(self) -> Tensor:
        generator = torch.Generator()
        generator.seed()

        config = TrainConfig.default_values()
        config.timestep_distribution = self.timestep_distribution
        config.min_noising_strength = self.min_noising_strength
        config.max_noising_strength = self.max_noising_strength
        config.noising_weight = self.noising_weight
        config.noising_bias = self.noising_bias

        return self._get_timestep_discrete(
            num_train_timesteps=1000,
            deterministic=False,
            generator=generator,
            batch_size=1000000,
            config=config,
        )


class TimestepDistributionWindow(ctk.CTkToplevel):
    def __init__(
            self,
            parent,
            config: TrainConfig,
            ui_state: UIState,
            *args, **kwargs,
    ):
        ctk.CTkToplevel.__init__(self, parent, *args, **kwargs)

        self.config = config
        self.ui_state = ui_state

        self.image_preview_file_index = 0

        self.title("时间步长分布")
        self.geometry("900x600")
        self.resizable(True, True)
        self.wait_visibility()
        self.grab_set()
        self.focus_set()

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.ax = None
        self.canvas = None

        frame = self.__content_frame(self)
        frame.grid(row=0, column=0, sticky='nsew')

        components.button(self, 1, 0, "ok", self.__ok)

    def __content_frame(self, master):
        frame = ctk.CTkScrollableFrame(master, fg_color="transparent")
        frame.grid_columnconfigure(0, weight=0)
        frame.grid_columnconfigure(1, weight=0)
        frame.grid_columnconfigure(2, weight=0)
        frame.grid_columnconfigure(3, weight=1)
        frame.grid_rowconfigure(5, weight=1)

        # timestep distribution
        components.label(frame, 0, 0, "时间步长分布",
                         tooltip="选择在训练期间采样时间步长的函数",
                         wide_tooltip=True)
        components.options(frame, 0, 1, [str(x) for x in list(TimestepDistribution)], self.ui_state,
                           "timestep_distribution")

        # min noising strength
        components.label(frame, 1, 0, "最小噪声强度",
                         tooltip="指定训练期间使用的最小噪声强度。这可以帮助改进构图，但会阻止训练更精细的细节")
        components.entry(frame, 1, 1, self.ui_state, "min_noising_strength")

        # max noising strength
        components.label(frame, 2, 0, "最大噪声强度",
                         tooltip="指定训练期间使用的最大噪声强度。这可以用来减少过拟合，但也减少了训练样本对整体图像构图的影响")
        components.entry(frame, 2, 1, self.ui_state, "max_noising_strength")

        # noising weight
        components.label(frame, 3, 0, "噪声权重",
                         tooltip="控制时间步长分布函数的权重参数。使用预览查看更多详细信息。")
        components.entry(frame, 3, 1, self.ui_state, "noising_weight")

        # noising bias
        components.label(frame, 4, 0, "噪声偏差",
                         tooltip="控制时间步长分布函数的偏差参数。使用预览查看更多详细信息。")
        components.entry(frame, 4, 1, self.ui_state, "noising_bias")

        # plot
        appearance_mode = AppearanceModeTracker.get_mode()
        background_color = self.winfo_rgb(ThemeManager.theme["CTkToplevel"]["fg_color"][appearance_mode])
        text_color = self.winfo_rgb(ThemeManager.theme["CTkLabel"]["text_color"][appearance_mode])
        background_color = f"#{int(background_color[0]/256):x}{int(background_color[1]/256):x}{int(background_color[2]/256):x}"
        text_color = f"#{int(text_color[0]/256):x}{int(text_color[1]/256):x}{int(text_color[2]/256):x}"

        fig, ax = plt.subplots()
        self.ax = ax
        self.canvas = FigureCanvasTkAgg(fig, master=frame)
        self.canvas.get_tk_widget().grid(row=0, column=3, rowspan=6)

        fig.set_facecolor(background_color)
        ax.set_facecolor(background_color)
        ax.spines['bottom'].set_color(text_color)
        ax.spines['left'].set_color(text_color)
        ax.spines['top'].set_color(text_color)
        ax.spines['right'].set_color(text_color)
        ax.tick_params(axis='x', colors=text_color, which="both")
        ax.tick_params(axis='y', colors=text_color, which="both")
        ax.xaxis.label.set_color(text_color)
        ax.yaxis.label.set_color(text_color)

        self.__update_preview()

        # update button
        components.button(frame, 6, 3, "Update Preview", command=self.__update_preview)

        frame.pack(fill="both", expand=1)
        return frame

    def __update_preview(self):
        generator = TimestepGenerator(
            timestep_distribution=self.config.timestep_distribution,
            min_noising_strength=self.config.min_noising_strength,
            max_noising_strength=self.config.max_noising_strength,
            noising_weight=self.config.noising_weight,
            noising_bias=self.config.noising_bias,
        )

        self.ax.cla()
        self.ax.hist(generator.generate(), bins=1000, range=(0, 999))
        self.canvas.draw()

    def __ok(self):
        self.destroy()
